# Mission: AI SEO Fan-Out Query Tool

## Overview
Develop a Python-based tool that automates the "Fan-Out Query" identification process used by AI search engines (like Gemini and ChatGPT). The tool will help SEO Specialists map out the sub-queries an LLM generates when processing a primary prompt.

## Objectives
1. **CSV Processing**: Allow users to upload/provide a CSV containing a list of "Primary Prompts".
2. **Fan-Out Generation**: For each prompt, use the Gemini API to simulate the "Fan-Out" process (decomposing the prompt into 5-8 intent-based sub-queries).
3. **Data Mapping**: Categorize these sub-queries into:
    - Specification (Detailed versions)
    - Entailment (Logically implied questions)
    - Follow-up (Next logical steps)
    - Local/Commercial (Intent-specific)
4. **Export**: Generate an output CSV/JSON that maps each Primary Prompt to its Fan-Out cluster.

## Tech Stack
- **Language**: Python 3.10+
- **API**: Google Gemini API (via `google-generativeai` SDK)
- **Data**: Pandas for CSV handling
- **UI**: Simple CLI or Streamlit dashboard (agent's choice)

## References
- Strategy based on Nectiv Digital's "Query Fan-Out" research.
- Focus on intent-depth and multi-entity reach.