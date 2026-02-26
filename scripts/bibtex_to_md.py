import re
from collections import defaultdict

import bibtexparser

CATEGORY_ORDER = [
    ("journal", "Journal articles"),
    ("conference", "Conference & workshop papers"),
    ("report", "Technical reports"),
]

LABEL_BY_CATEGORY = {
    "journal": ("Journal", "journal"),
    "conference": ("Conference", "conf"),
    "report": ("Report", "report"),
}

NAME_PARTICLES = {
    "da",
    "de",
    "del",
    "della",
    "den",
    "der",
    "des",
    "di",
    "du",
    "la",
    "le",
    "van",
    "von",
}


def clean_text(value: str) -> str:
    if not value:
        return ""
    text = str(value).replace("\n", " ").replace("\t", " ").strip()
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_year(value: str) -> str:
    year = clean_text(value)
    return year if year else "Unknown"


def year_sort_key(value: str) -> tuple:
    year = normalize_year(value)
    try:
        return (1, int(year))
    except ValueError:
        return (0, year)


def read_bibtex_file(filename) -> dict:
    """Read a BibTeX file and return entries grouped by publication year."""
    with open(filename, "r", encoding="utf-8") as bibtex_file:
        bibtex_str = bibtex_file.read()
    bib_database = bibtexparser.loads(bibtex_str)
    entries = bib_database.entries

    entries.sort(
        key=lambda entry: (
            year_sort_key(entry.get("year", "")),
            clean_text(entry.get("title", "")).lower(),
        ),
        reverse=True,
    )

    entries_by_year = defaultdict(list)
    for entry in entries:
        year = normalize_year(entry.get("year", ""))
        entries_by_year[year].append(entry)

    return entries_by_year


def format_single_author(raw_author: str) -> str:
    raw_author = clean_text(raw_author)
    if not raw_author:
        return ""

    if "," in raw_author:
        surname, given = [part.strip() for part in raw_author.split(",", 1)]
        given_tokens = [token for token in given.split() if token]
    else:
        tokens = [token for token in raw_author.split() if token]
        if len(tokens) == 1:
            return tokens[0]
        surname = tokens[-1]
        given_tokens = tokens[:-1]
        while given_tokens and given_tokens[-1].lower() in NAME_PARTICLES:
            surname = f"{given_tokens.pop()} {surname}"

    initials = []
    for token in given_tokens:
        normalized = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ]", "", token)
        if normalized:
            initials.append(f"{normalized[0].upper()}.")

    if initials:
        return f"{' '.join(initials)} {surname}"
    return surname


def format_authors(authors: str) -> str:
    if not authors:
        return "Unknown authors"
    authors = clean_text(authors)
    formatted_authors = [
        format_single_author(raw_author)
        for raw_author in re.split(r"\s+and\s+", authors)
        if raw_author.strip()
    ]
    return ", ".join(author for author in formatted_authors if author) or "Unknown authors"


def get_keywords(entry: dict) -> str:
    keywords = clean_text(entry.get("keywords", ""))
    return keywords.lower()


def classify_entry(entry: dict) -> str:
    """Classify publication type using keywords (workshops are conferences)."""
    keywords = get_keywords(entry)

    if any(token in keywords for token in ("report", "techreport", "technical report")):
        return "report"
    if any(token in keywords for token in ("conference", "workshop", "national")):
        return "conference"
    if "journal" in keywords:
        return "journal"

    entrytype = entry.get("ENTRYTYPE", "").lower()
    if entrytype in {"article"}:
        return "journal"
    if entrytype in {"inproceedings", "conference", "proceedings"}:
        return "conference"
    if entrytype in {"techreport", "report"}:
        return "report"
    return "conference"


def doi_link(entry: dict) -> str:
    doi = clean_text(entry.get("doi", ""))
    if not doi:
        return ""
    return f"https://doi.org/{doi}"


def pdf_link(entry: dict) -> str:
    pdf = clean_text(entry.get("pdf", "")) or clean_text(entry.get("PDF", ""))
    if pdf:
        return pdf

    url = clean_text(entry.get("url", ""))
    if url.lower().endswith(".pdf"):
        return url

    eprint = clean_text(entry.get("eprint", ""))
    eprint_type = clean_text(entry.get("eprinttype", "")).lower()
    if eprint and "arxiv" in eprint_type:
        return f"https://arxiv.org/pdf/{eprint}.pdf"

    return ""


def render_links(entry: dict, category: str) -> str:
    doi_url = doi_link(entry)
    pdf_url = pdf_link(entry)
    links = []

    if category in {"journal", "conference"}:
        if doi_url:
            links.append(f"[doi]({doi_url})")
        if pdf_url:
            links.append(f"[pdf]({pdf_url})")
    else:
        if pdf_url:
            links.append(f"[pdf]({pdf_url})")
        elif clean_text(entry.get("url", "")):
            links.append(f"[pdf]({clean_text(entry.get('url', ''))})")
        elif doi_url:
            links.append(f"[pdf]({doi_url})")

    return " ".join(links)


def get_publication_venue(entry: dict, category: str) -> str:
    if category == "journal":
        return clean_text(entry.get("journal", "")) or "Journal"
    if category == "conference":
        return (
            clean_text(entry.get("booktitle", ""))
            or clean_text(entry.get("journal", ""))
            or "Conference proceedings"
        )
    return (
        clean_text(entry.get("institution", ""))
        or clean_text(entry.get("publisher", ""))
        or clean_text(entry.get("school", ""))
        or clean_text(entry.get("journal", ""))
        or "Technical report"
    )


def render_entry(entry: dict, category: str) -> str:
    label, css_class = LABEL_BY_CATEGORY[category]
    badge = f"[{label}]{{.pubtype .{css_class}}}"
    title = clean_text(entry.get("title", "")) or "Untitled"
    authors = format_authors(entry.get("author", ""))
    venue = get_publication_venue(entry, category)
    year = normalize_year(entry.get("year", ""))
    links = render_links(entry, category)

    rendered = f"{badge} **{title}**. {authors}. *{venue}*, {year}."
    if links:
        rendered += f" {links}"
    return rendered


def generate_list_by_year(entries_by_year: dict) -> str:
    """Generate a Markdown bibliography list grouped by year and publication type."""
    md_lines = []
    for year in sorted(entries_by_year.keys(), key=year_sort_key, reverse=True):
        md_lines.append(f"## {year}")
        md_lines.append("")

        entries_by_category = defaultdict(list)
        for entry in entries_by_year[year]:
            category = classify_entry(entry)
            entries_by_category[category].append(entry)

        for category, heading in CATEGORY_ORDER:
            entries = entries_by_category.get(category, [])
            if not entries:
                continue
            md_lines.append(f"### {heading}")
            for entry in entries:
                md_lines.append(f"1. {render_entry(entry, category)}")
            md_lines.append("")

    years = len(entries_by_year)
    total_entries = sum(len(entries) for entries in entries_by_year.values())
    print(f"Processed {total_entries} entries from {years} years.")

    return "\n".join(md_lines).rstrip() + "\n"


def write_into_file(entries_by_year: dict, destination_path: str, destination_div: str) -> None:
    """Write generated references between `<!-- div -->` and `<!-- /div -->` markers."""
    with open(destination_path, "r", encoding="utf-8") as file:
        md = file.read()

    start_marker = f"<!-- {destination_div} -->"
    end_marker = f"<!-- /{destination_div} -->"
    start = md.find(start_marker)
    if start == -1:
        raise ValueError(f"Cannot find marker: {start_marker}")

    end = md.rfind(end_marker)
    if end == -1 or end < start:
        end = len(md)
        suffix = ""
    else:
        suffix = md[end + len(end_marker):]

    generated = (
        f"{start_marker}\n\n"
        f"{generate_list_by_year(entries_by_year)}\n"
        f"{end_marker}\n"
    )
    md = md[:start] + generated + suffix

    with open(destination_path, "w", encoding="utf-8") as file:
        file.write(md)


if __name__ == "__main__":
    import os
    import sys

    # # Ensure UTF-8 encoding for stdout to handle diacritics
    # if sys.platform == 'win32':
    #     import io
    #     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    #     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # if not os.getenv("QUARTO_PROJECT_RENDER_ALL"):
    #     exit()

    OUTPUT_FILENAME: str = "publications/index.qmd"
    INPUT_FILENAME: str = "publications/mybibliography.bib"

    print(f"Rendering bibliography...")
    print("Reading BibTeX file from " + INPUT_FILENAME)
    entries = read_bibtex_file(INPUT_FILENAME)

    print("Writing bibliography to " + OUTPUT_FILENAME)
    write_into_file(entries, OUTPUT_FILENAME, "references")
    print("Done.")
