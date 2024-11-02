from datetime import datetime


def generate_query_refinement_prompt(query: str, context: str = "", refined_query: str = '', title: str = '', description: str = '') -> str:
    context = context if context else ""
    extra_desc = ""
    if (title):
        extra_desc += f"- This query is related to a topic called title: {title}\n"
    if (description):
        extra_desc += f"- Description: {description}\n"
    prompt = f"""
    # Query Refinement Task

You refine user queries for semantic search in a RAG system, prioritizing the latest user query while considering previous queries if relevant.

## Input
- Current Query: {query}
- Keywords: {refined_query if refined_query else "N/A"}
- Chat Context: {context if context else "N/A"}
{extra_desc}
{title}
    - Shows user's previous queries, if available
    - Indicates user's information-seeking path if it aligns with the current query

- If required, consider today's date and time as: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Context Analysis
Focus on the most recent query, unless it's a clear progression from previous queries. If the latest query diverges significantly:
- Give full priority to the current query
- Ignore unrelated past context

Otherwise, when previous queries are related:
- Identify user's main topics of interest
- Trace question progression and key terms
- Understand search patterns

## Query Guidelines
For short queries (<10 words):
- Expand using the current query and relevant past context
- If unrelated, build entirely on the current query
- Create a 15-25 word natural query that matches the search intent

For long queries (≥10 words):
- Extract core intent from the current query first
- Only integrate previous queries if they align
- Focus on refining the main topic and clarifying any ambiguous terms

## Output Rules
- No explanations
- No bullet points
- Directly return the refined query with clear user intent
- Prioritize the current query if unrelated

Remember: Create one clear, search-optimized sentence that builds on user's previous queries and current intent. Don't include any additional context or explanations. Strictly focus on refining the query for semantic search in a RAG system and return it.
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
