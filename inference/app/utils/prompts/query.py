def generate_query_refinement_prompt(query: str, context: str = "", refined_query: str = '') -> str:
    context = context if context else ""
    prompt = f"""
Given the following user query and context, refine the query to improve its effectiveness for vector database search:

User Query: {query}
Query without stop words: {refined_query if refined_query else "No refined query available"}
Context: {context if context else "No additional context provided"}

Your task:
1. Identify the main concepts and intent of the query.
2. Expand on these concepts with relevant synonyms or related terms.
3. Incorporate any relevant context to make the query more specific.
4. Ensure the refined query maintains the original intent while being more comprehensive.

Provide the refined query in a clear, concise format suitable for vector database search.
"""

    return prompt
