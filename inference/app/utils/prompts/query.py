def generate_query_refinement_prompt(query: str, context: str = "", refined_query: str = '') -> str:
    context = context if context else ""
    prompt = f"""
Given the following user query and context, refine the query to improve its effectiveness for semantic search in a RAG system:

User Query: {query}
Query without stop words: {refined_query if refined_query else "No refined query available"}
Context: {context if context else "No additional context provided"}

Your task:
1. Analyze the main concepts and intent of the query.
2. If the original query is short (less than 10 words):
   - Expand it into a more detailed question or statement that captures the user's intent.
   - Incorporate relevant context if available.
   - Aim for a refined query of 15-25 words.
3. If the original query is long (10 words or more):
   - Summarize it to capture the core intent and key concepts.
   - Remove any redundant or less important information.
   - Aim for a refined query of 10-20 words.
4. Ensure the refined query is a natural language phrase or sentence, not a list of keywords.
5. The refined query should maintain the original intent while being optimized for semantic search.

Provide the refined query as a single, clear sentence suitable for semantic search in a RAG system. Do not use bullet points or numbered lists in your response.
"""
    return prompt
