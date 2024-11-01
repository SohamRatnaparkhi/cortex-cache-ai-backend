def generate_query_refinement_prompt(query: str, context: str = "", refined_query: str = '', title: str = '', description: str = '') -> str:
    context = context if context else ""
    extra_desc = ""
    if (title):
        extra_desc += f"This query is related to a topic called title: {title}\n"
    if (description):
        extra_desc += f"Description: {description}\n"
    prompt = f"""
   # Query Refinement Task

You refine user queries for semantic search in a RAG system, considering current and previous user queries.

## Input
- Current Query: {query}
- Keywords: {refined_query if refined_query else "N/A"}
- Chat Context: {context if context else "N/A"}
    - Contains user's previous queries only
    - Shows user's information seeking path
    - Reveals user's topic progression

## Context Analysis
Extract from previous queries:
- User's main topics of interest
- Question progression
- Key terms used
- Specific references
- Search patterns

## Query Guidelines
For short queries (<10 words):
- Expand using context from previous queries
- Connect to user's earlier questions
- Build on established search intent
- Create 15-25 word natural query
- Include recurring concepts

For long queries (≥10 words):
- Extract core intent
- Keep concepts from related previous queries
- Maintain search direction
- Create 10-20 word focused query
- Preserve key user terms

## Contextual Integration
- Build on previous search intent
- Use terms consistent with user's vocabulary
- Consider question sequence
- Connect related queries
- Resolve ambiguous terms

## Format
Return the refined query here without any headings or anything else. Directly start with the refined query.

## Output Rules
- No explanations
- No bullet points
- No additional text
- Just the refined query with prefix

Remember: Create one clear, search-optimized sentence that builds on user's previous queries and current intent.
"""
    return prompt

#     prompt = f"""
# Given the following user query and context, refine the query to improve its effectiveness for semantic search in a RAG system:

# User Query: {query}
# Query without stop words: {refined_query if refined_query else "No refined query available"}
# Context: {context if context else "No additional context provided"}

# Your task:
# 1. Analyze the main concepts and intent of the query.
# 2. If the original query is short (less than 10 words):
#    - Expand it into a more detailed question or statement that captures the user's intent.
#    - Incorporate relevant context if available.
#    - Aim for a refined query of 15-25 words.
# 3. If the original query is long (10 words or more):
#    - Summarize it to capture the core intent and key concepts.
#    - Remove any redundant or less important information.
#    - Aim for a refined query of 10-20 words.
# 4. Ensure the refined query is a natural language phrase or sentence, not a list of keywords.
# 5. The refined query should maintain the original intent while being optimized for semantic search.

# Provide the refined query as a single, clear sentence suitable for semantic search in a RAG system. Do not use bullet points or numbered lists in your response.
# """
