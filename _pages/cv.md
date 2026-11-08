---
layout: archive
title: "CV"
permalink: /cv/
author_profile: true
redirect_from:
  - /resume
---

## Research Interests

Code intelligence, repository-level code evolution, code retrieval, static program analysis, graph algorithms, and LLM agents.

**Research internship interests:** code intelligence / LLM agents.

**Contact:** [{{ site.author.email }}](mailto:{{ site.author.email }}).

## Education

### Peking University — School of Computer Science

**Direct-entry Ph.D. in Computer Science and Technology** · September 2025–June 2030 (expected)

- Research area: software engineering.

### Beijing Institute of Technology — School of Computer Science

**Bachelor's degree in Computer Science and Technology** · September 2021–June 2025

- Average credit-weighted score over the first three undergraduate years: **92.7/100**.
- Rank over the first three undergraduate years: **1/162** in the major.

## Honors and Awards

- **National Scholarship**, twice.
- **Beijing Outstanding Student** (北京市三好学生).
- **Beijing Outstanding Graduate** (北京市优秀毕业生).

## Research Experience and Publications

{% include research-list.html detailed=true %}

## Course Project

### Repetitive Generation Analysis and Neuron Intervention in Language Models

**Computational linguistics course project** · September 2025–January 2026

**Code:** [github.com/uniqueFranky/LLMRep](https://github.com/uniqueFranky/LLMRep)

- Reproduced a method for identifying repetition-related neurons. Used PyTorch forward hooks to collect MLP activations, selected candidate neurons by differences in mean activation before and after repetition, and zeroed their activations during inference.
- In the course report's **GPT-2 / IWSLT** experiment, neuron suppression alone reduced **Rep-3 from 70.66% to 24.54%**, while **perplexity increased from 1.589 to 3.732**. These results show a repetition–perplexity trade-off, not a lossless improvement.

## Teaching Experience

{% include teaching-experience.html %}

## Technical Skills

- **Programming:** Java, Python, JavaScript, C++.
- **Research and development:** static program analysis, code retrieval, graph algorithms, and LLM agent tooling.
