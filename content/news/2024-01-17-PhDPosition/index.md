---
title: PostDoc Position @NOKIA Bell Labs, @TRiBE/NEO-INRIA
pub_link: ""
publication: "Post-Doctoral - Research Visit F/M Model placement in inference delivery networks"
publishdate: "2024-02-14"
author: "Nadjib Achir"
date: "2024-02-14"
# slug: mentoring-award
categories:
  - news
  - news articles
tags: [PostDoc Position]
# draft: true
---

<!--more-->

# Context

This PostDos is funded by the challenge Inria-Nokia Bell Labs: LearnNet (Learning Networks)

# Assignment

## Context

In this postdoc, we will study the problem of AI model placement in an IDN. This is a challenging optimization problem that involves a non-trivial tradeoff between model effectiveness, inference latency, and resource availability while also dealing with the natural dynamicity of the network, e.g., due to users’ request process or changes in available computing and communication resources.

We will also consider other metrics, such as energy consumption, in the objective functions and networking constraints for systems where the network presents some inelasticity (see also [1]). We will leverage multi-objective optimization techniques (e.g., Pareto efficient solutions) and transfer learning techniques to adapt models across nodes with different levels of knowledge and resource availability. We will also rely on online learning approaches to achieve model placements with adversarial guarantees regarding regret.

In comparison to our preliminary work in [2] or [3], we will allow models to be split across multiple nodes [4,5,6]. In particular, we aim to compare specific model splitting techniques, with or without the insertion of bottlenecks [7,8] (reference [8] is also the result of NEO-AIRL cooperation), in terms of performance metrics like inference delay and network load. We will evaluate different methodologies to estimate online the quality of an inference [9].

This evaluation may also consider scenarios with significant heterogeneity of the nodes, such as in the scenario of embedded Edge AI or even more with TinyML (resources possibly lower by orders of magnitude but possibly a massive number of devices).

## Collaboration

This postdoc will be recruited and hosted at Inria Saclay and supervised by Tribe (INRIA), Neo (INRIA), and AIRL (Nokia)

## References

[1] Kinda Khawam et al. “Edge Learning as a Hedonic Game in LoRaWAN”. ICC 2023 - IEEE International Conference on Communications. 2023.

[2] Tareq Si Salem et al. “Towards inference delivery networks: distributing machine learning with optimality guarantees.” In: 19th Mediterranean Communication and Computer Networking Conference (MEDCOMNET 2021). Ibiza (virtual), Spain: IEEE, June 2021, pp. 1–8.

[3] Wassim Seifeddine, Cédric Adjih, and Nadjib Achir. “Dynamic Hierarchical Neural Network Offloading in IoT Edge Networks.” In: PEMWN 2021 - 10th IFIP International Conference on Performance Evaluation and Modeling in Wireless and Wired Networks. Ottawa / Virtual, Canada: IEEE, Nov. 2021, pp. 1–6.

[4] Surat Teerapittayanon, Bradley McDanel, and Hsiang-Tsung Kung. “Branchynet: Fast inference via early exiting from deep neural networks”. In: 2016 23rd International Conference on Pattern Recognition (ICPR). IEEE, 2016, pp. 2464-2469

[5] S. Teerapittayanon, B. McDanel, and H. T. Kung. “Distributed Deep Neural Networks Over the Cloud, the Edge and End Devices”. In: 2017 IEEE 37th International Conference on Distributed Computing Systems (ICDCS). ISSN: 1063-6927. June 2017, pp. 328–339.

[6] Yoshitomo Matsubara, Marco Levorato, and Francesco Restuccia. “Split Computing and Early Exiting for Deep Learning Applications: Survey and Research Challenges”. In: ACM Computing Surveys 55.5 (Dec. 2022), 90:1–90:30. issn:0360-0300.

[7] Yoshitomo Matsubara et al. “BottleFit: Learning Compressed Representations in Deep Neural Networks for Effective and Efficient Split Computing”. English. In: IEEE Computer Society, June 2022, pp. 337–346. isbn: 978-1-66540-876-9.

[8] Gabriele Castellano et al. “Regularized Bottleneck with Early Labeling”. In: ITC 2022 - 34th International Teletraffic Congress. Shenzhen, China, Sept. 2022.

[9] Ira Cohen and Moises Goldszmidt. “Properties and benefits of calibrated classifiers”. In: European Conference on Principles of Data Mining and Knowledge Discovery. Springer, 2004, pp. 125–136.
