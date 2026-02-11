# Skill: SEO Fan-Out Analyzer (Grounding)

**Description**: Analyzes primary SEO prompts by leveraging Google Search Grounding to capture the actual search queries an AI model performs to answer them.

## Instructions
When triggered with a prompt or a CSV file:

1. **Context Setup**: Identify the target market (e.g., "Denmark") and the primary user query.
2. **Grounding Prompt**: Construct a prompt designed to trigger a comprehensive search:
   > "Context: Target market is {target_country}. User Query: {prompt}. Please perform a comprehensive search to provide a detailed answer. Cover all aspects including intent, competitors, and background."
3. **Execution**: Call the Gemini API with the `google_search` tool enabled.
4. **Extraction**: Parse the response's `grounding_metadata` to extract the `web_search_queries`.
5. **Output**: Present the list of raw search queries that were actually performed by the model.

## Example
**Input**: "Best CRM for small law firms" (Target: US)

** captured Fan-Out Queries**:
1. "best crm for small law firms 2024"
2. "clio vs practice panther pricing"
3. "legal crm features comparison"
4. "lawmatics reviews"