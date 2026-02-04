# Skill: SEO Fan-Out Analyzer

**Description**: Analyzes SEO prompts to identify the "Fan-Out" sub-queries an AI model would likely search for to ground its answer.

## Instructions
When triggered with a prompt or a CSV file:
1. Parse the input to identify the core entity and primary intent.
2. Act as a "Query Decomposer."
3. Generate exactly 6 "Fan-Out Queries" for each prompt using these categories:
    - **Search Intent**: What is the immediate factual need?
    - **Contextual Layer**: What background information is required?
    - **Comparative Layer**: What alternatives or competitors should be checked?
    - **Prerequisite**: What must the user know first?
    - **Next Step**: What will the user ask after this?
    - **Entity Deep-Dive**: Specifics about the brand/product mentioned.
4. Format the output into a structured table.

## Example
**Input**: "Best CRM for small law firms"
**Fan-Out Queries**:
1. "Top rated CRM software for legal industry 2026"
2. "CRM features specifically for law firm case management"
3. "Clio vs MyCase vs HubSpot for small legal teams"
4. "Affordable CRM pricing for solo practitioners"
5. "How to migrate legal data from Excel to CRM"
6. "Security and compliance requirements for legal CRMs"