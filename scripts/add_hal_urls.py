#!/usr/bin/env python3
"""Add HAL publication URLs to BibTeX entries when matches are found."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from time import sleep

HAL_API_URL = "https://api.archives-ouvertes.fr/search/"
ENTRY_START_RE = re.compile(r"@([A-Za-z]+)\s*{")
HEADER_RE = re.compile(r"@(?P<type>[A-Za-z]+)\s*{\s*(?P<key>[^,]+),", re.S)


@dataclass
class BibEntry:
    start: int
    end: int
    block: str
    entry_type: str
    key: str
    fields: dict[str, str]


@dataclass
class LookupState:
    had_api_error: bool = False


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 1
    i = open_index + 1
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def strip_outer_delimiters(value: str) -> str:
    value = value.strip()
    if len(value) >= 2:
        if value[0] == "{" and value[-1] == "}":
            return value[1:-1].strip()
        if value[0] == '"' and value[-1] == '"':
            return value[1:-1].strip()
    return value


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    n = len(body)

    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break

        name_start = i
        while i < n and (body[i].isalnum() or body[i] in "_-"):
            i += 1
        field_name = body[name_start:i].strip().lower()
        if not field_name:
            i += 1
            continue

        while i < n and body[i].isspace():
            i += 1
        if i >= n or body[i] != "=":
            while i < n and body[i] != ",":
                i += 1
            continue

        i += 1
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break

        if body[i] == "{":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            raw_value = body[i:j]
            i = j
        elif body[i] == '"':
            j = i + 1
            escaped = False
            while j < n:
                char = body[j]
                if char == '"' and not escaped:
                    j += 1
                    break
                escaped = char == "\\" and not escaped
                if char != "\\":
                    escaped = False
                j += 1
            raw_value = body[i:j]
            i = j
        else:
            j = i
            while j < n and body[j] not in ",\r\n":
                j += 1
            raw_value = body[i:j]
            i = j

        fields[field_name] = strip_outer_delimiters(raw_value)
        while i < n and body[i].isspace():
            i += 1
        if i < n and body[i] == ",":
            i += 1

    return fields


def parse_bibtex_entries(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    idx = 0
    while True:
        match = ENTRY_START_RE.search(text, idx)
        if not match:
            break

        open_brace = text.find("{", match.start())
        if open_brace == -1:
            idx = match.end()
            continue

        close_brace = find_matching_brace(text, open_brace)
        if close_brace == -1:
            idx = match.end()
            continue

        block = text[match.start():close_brace + 1]
        header_match = HEADER_RE.match(block)
        if not header_match:
            idx = close_brace + 1
            continue

        body = block[header_match.end():-1]
        entry = BibEntry(
            start=match.start(),
            end=close_brace + 1,
            block=block,
            entry_type=header_match.group("type").strip(),
            key=header_match.group("key").strip(),
            fields=parse_fields(body),
        )
        entries.append(entry)
        idx = close_brace + 1

    return entries


def normalize_text(value: str) -> str:
    value = strip_outer_delimiters(value)
    value = re.sub(r"\\[a-zA-Z]+\s*", " ", value)
    value = value.replace("{", " ").replace("}", " ")
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^0-9A-Za-z]+", " ", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def clean_doi(value: str) -> str:
    doi = strip_outer_delimiters(value).strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi.strip()


def escape_solr_phrase(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def get_hal_docs(query: str, rows: int, timeout: float) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "rows": rows,
            "wt": "json",
            "fl": "uri_s,halId_s,title_s,title_t,doiId_id,publicationDateY_i",
        }
    )
    url = f"{HAL_API_URL}?{params}"

    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("response", {}).get("docs", [])


def coerce_first(value: object) -> str:
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    if value is None:
        return ""
    return str(value).strip()


def get_hal_url(doc: dict) -> str:
    uri = coerce_first(doc.get("uri_s"))
    if uri:
        return uri
    hal_id = coerce_first(doc.get("halId_s"))
    if hal_id:
        return f"https://hal.science/{hal_id}"
    return ""


def get_title_from_doc(doc: dict) -> str:
    title = coerce_first(doc.get("title_s"))
    if title:
        return title
    return coerce_first(doc.get("title_t"))


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def find_hal_url_for_entry(
    doi: str,
    title: str,
    year: str,
    max_rows: int,
    timeout: float,
    cache: dict[tuple[str, str], str | None],
    state: LookupState,
) -> str | None:
    normalized_doi = clean_doi(doi)
    normalized_title = normalize_text(title)
    normalized_year = re.sub(r"[^0-9]", "", year or "")

    if normalized_doi:
        cache_key = ("doi", normalized_doi.lower())
        if cache_key in cache:
            return cache[cache_key]

        query = f'doiId_id:"{escape_solr_phrase(normalized_doi)}"'
        try:
            docs = get_hal_docs(query=query, rows=1, timeout=timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            state.had_api_error = True
            return None

        url = get_hal_url(docs[0]) if docs else None
        cache[cache_key] = url
        if url:
            return url

    if not normalized_title:
        return None

    cache_key = ("title", normalized_title)
    if cache_key in cache:
        return cache[cache_key]

    query = f'title_t:"{escape_solr_phrase(title)}"'
    try:
        docs = get_hal_docs(query=query, rows=max_rows, timeout=timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        state.had_api_error = True
        return None

    best_url: str | None = None
    best_score = 0.0
    for doc in docs:
        doc_url = get_hal_url(doc)
        doc_title = get_title_from_doc(doc)
        if not doc_url or not doc_title:
            continue

        score = title_similarity(title, doc_title)
        doc_year = re.sub(r"[^0-9]", "", coerce_first(doc.get("publicationDateY_i")))
        year_matches = bool(normalized_year and doc_year and normalized_year == doc_year)
        if score >= 0.9 or (score >= 0.8 and year_matches):
            if score > best_score:
                best_score = score
                best_url = doc_url

    cache[cache_key] = best_url
    return best_url


def detect_indent(block: str) -> str:
    for line in block.splitlines():
        stripped = line.lstrip(" \t")
        if stripped and "=" in stripped and not stripped.startswith("@"):
            indent = line[: len(line) - len(stripped)]
            return indent or "  "
    return "  "


def insert_or_replace_hal_field(
    block: str,
    field_name: str,
    hal_url: str,
    overwrite: bool,
) -> str:
    line_ending = "\r\n" if "\r\n" in block else "\n"
    closing_index = block.rfind("}")
    if closing_index == -1:
        return block

    pattern = re.compile(rf"(^\s*{re.escape(field_name)}\s*=\s*)(\{{.*?\}}|\".*?\"|[^,\n]+)(\s*,?)",
                         re.IGNORECASE | re.MULTILINE | re.DOTALL)

    if overwrite:
        replaced, count = pattern.subn(rf"\1{{{hal_url}}}\3", block, count=1)
        if count > 0:
            return replaced

    body = block[:closing_index].rstrip()
    indent = detect_indent(block)
    if not body.endswith(","):
        body += ","
    return f"{body}{line_ending}{indent}{field_name} = {{{hal_url}}},{line_ending}}}"


def process_bib_file(
    input_path: Path,
    output_path: Path,
    field_name: str,
    overwrite: bool,
    timeout: float,
    max_rows: int,
    delay: float,
) -> tuple[int, int, int, int, bool]:
    text = input_path.read_text(encoding="utf-8")
    entries = parse_bibtex_entries(text)
    cache: dict[tuple[str, str], str | None] = {}
    state = LookupState()

    updates: list[tuple[int, int, str]] = []
    updated_count = 0
    existing_count = 0
    not_found_count = 0
    skipped_count = 0

    existing_fields = {field_name.lower(), "halurl", "hal_url"}

    for index, entry in enumerate(entries):
        fields = entry.fields
        has_hal_field = any(name in fields for name in existing_fields)
        if has_hal_field and not overwrite:
            existing_count += 1
            continue

        doi = fields.get("doi", "")
        title = fields.get("title", "")
        year = fields.get("year", "")
        if not doi and not title:
            skipped_count += 1
            continue

        hal_url = find_hal_url_for_entry(
            doi=doi,
            title=title,
            year=year,
            max_rows=max_rows,
            timeout=timeout,
            cache=cache,
            state=state,
        )

        if hal_url:
            new_block = insert_or_replace_hal_field(
                block=entry.block,
                field_name=field_name,
                hal_url=hal_url,
                overwrite=overwrite,
            )
            updates.append((entry.start, entry.end, new_block))
            updated_count += 1
        else:
            not_found_count += 1

        if delay > 0 and index < len(entries) - 1:
            sleep(delay)

    for start, end, new_block in reversed(updates):
        text = text[:start] + new_block + text[end:]

    output_path.write_text(text, encoding="utf-8")
    return updated_count, existing_count, not_found_count, skipped_count, state.had_api_error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Find matching publications on HAL and add a HAL URL field to each "
            "BibTeX entry."
        )
    )
    parser.add_argument("input_bib", help="Path to input BibTeX file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output BibTeX file (default: update input file in place)",
    )
    parser.add_argument(
        "--field-name",
        default="hal_url",
        help="BibTeX field to write for HAL URL (default: hal_url)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing HAL field values when present",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds for HAL API requests (default: 10)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=5,
        help="Max HAL results to inspect for title search (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay in seconds between API calls (default: 0.1)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_bib)
    if not input_path.exists():
        parser.error(f"Input file does not exist: {input_path}")

    output_path = Path(args.output) if args.output else input_path

    updated, existing, not_found, skipped, had_api_error = process_bib_file(
        input_path=input_path,
        output_path=output_path,
        field_name=args.field_name,
        overwrite=args.overwrite,
        timeout=args.timeout,
        max_rows=max(1, args.rows),
        delay=max(0.0, args.delay),
    )

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Updated entries: {updated}")
    print(f"Already had HAL field: {existing}")
    print(f"No HAL match found: {not_found}")
    print(f"Skipped (no title/doi): {skipped}")
    if had_api_error:
        print(
            "Warning: at least one HAL API request failed. "
            "Please check network access and retry."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
