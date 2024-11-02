def get_search_prompt(user_query: str) -> str:
    try:
        return f"""You are an AI assistant helping to convert natural language memory search queries into semantic search-optimized queries. Your task is to:

    1. Extract the core concepts and important terms from the user's query
    2. Remove conversational fillers and meta-language
    3. Maintain the semantic intent of the search
    4. Focus on descriptive, content-rich terms
    5. Preserve emotional and contextual qualifiers that matter for memory searches

    Input: "{user_query}"

    Guidelines:
    - Remove phrases like "find me", "show me", "I want to see", "can you get", etc.
    - Keep emotional qualifiers IF ANY (happy, sad, exciting, etc.) as they're relevant for memories
    - Preserve time-related terms IF ANY (summer, last year, childhood, etc.)
    - Keep location references IF ANY
    - Maintain references to people and relationships IF ANY
    - Include activity and event types IF ANY 
    - Preserve sensory descriptions (how things looked, felt, sounded, etc.)
    - Don't unnecessarily add emotional qualifiers or time/location/relationship/event references if they're not present in the original query

    Output the transformed search query in the format
    TRANSFORMED QUERY: <your refined query here>

    Remember, the output will be used for semantic vector search, so focus on meaningful content words and phrases that capture the essence of what memories the user wants to find.
    """
    except Exception as e:
        print(f"Error in get_search_prompt: {str(e)}")
        raise RuntimeError(f"Error occurred while getting search prompt: {e}")
