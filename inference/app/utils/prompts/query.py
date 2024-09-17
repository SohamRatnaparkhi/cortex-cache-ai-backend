def generate_generalized_prompts(context: str, query: str, refined_query: str, num_prompts: int = 5) -> list:
    base_prompts = [
        f"""
Analyze the given query in the context of information retrieval:

Original Query: {query}
Initial Refinement: {refined_query}
Context: {context if context != "" else "No additional context provided"}

Your task:
1. Identify the core concepts and entities in the query.
2. Determine the implicit intent behind the query.
3. Consider potential ambiguities or multiple interpretations.
4. Suggest specific technical terms or jargon related to the query's domain.
5. Propose synonyms or related concepts that could enhance the search.

Based on this analysis, refine the query to be more specific, comprehensive, and optimized for vector database search. Ensure the refined query captures the original intent while expanding its scope for better results.
""",
    f"""
Enhance the query for domain-specific vector search:

Original Query: {query}
Initial Refinement: {refined_query}
Context: {context if context != "" else "No additional context provided"}

Your task:
1. Identify the primary domain(s) relevant to the query (e.g., technology, science, business).
2. Incorporate domain-specific terminology and concepts.
3. Consider recent trends or developments in the field that might be relevant.
4. Add any necessary qualifiers to narrow the scope within the domain.
5. Ensure the query is formulated to retrieve the most up-to-date and relevant information.

Refine the query to be highly specific and tailored to the identified domain(s), optimizing it for vector database search.""",

f"""
Expand the query semantically for comprehensive vector search:

Original Query: {query}
Initial Refinement: {refined_query}
Context: {context if context != "" else "No additional context provided"}

Your task:
1. Identify key concepts in the query and expand them with related terms.
2. Consider different levels of abstraction (more general and more specific terms).
3. Include potential synonyms and closely related concepts.
4. Think about different aspects or facets of the main topic that might be relevant.
5. Incorporate any contextual clues to broaden the query's scope while maintaining relevance.

Create a semantically rich query that captures a wide range of potentially relevant information while staying true to the original intent.""",

f"""
Decompose and refine the query for detailed vector search:

Original Query: {query}
Initial Refinement: {refined_query}
Context: {context if context != "" else "No additional context provided"}

Your task:
1. Break down the query into its fundamental components or sub-questions.
2. Identify any assumptions in the query and make them explicit.
3. Consider different angles or perspectives from which the query could be approached.
4. Formulate a series of related queries that together comprehensively cover the topic.
5. Ensure each answer is big enough to be a good answer.
6. If users asks to generate a blog or a poem then generate accordingly.

Refine the query by creating a comprehensive set of related queries that together address all aspects of the original question.
""",

f"""
Integrate context for a highly targeted vector search query:

Original Query: {query}
Initial Refinement: {refined_query}
Context: {context if context != "" else "No additional context provided"}

Your task:
1. Analyze the provided context and identify key elements relevant to the query.
2. Incorporate contextual information to make the query more specific and targeted.
3. Consider any time-sensitive or location-specific aspects mentioned in the context.
4. Identify any contradictions between the query and context, and resolve them in the refinement.
5. Ensure the refined query leverages the context to improve search precision.

Create a refined query that seamlessly integrates relevant contextual information to enhance search accuracy and relevance.

"""

]
    rule = f"""
    If the context is not provided, then don't rely on it, but dont hallucinate at all. Strictly stick near about original query while still refining it.
    Structure your response as a JSON object with the following keys:
    - "refined_query": The refined query based on the original query and context.
    The value to refined_query should strictly be a string and nothing else.
    Example:
    {{
        "refined_query": "The refined query based on the original query and context."
    }}
    """

    for i in range(num_prompts):
        base_prompts[i] = rule + base_prompts[i] + rule

    return base_prompts





