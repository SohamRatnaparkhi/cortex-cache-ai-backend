"""Query Analysis and Refinement Module"""

import re
from datetime import datetime
from typing import Literal


def detect_code_query(query: str) -> bool:
    """Detects if a query is likely code-related based on various heuristics."""

    code_indicators = [
        r'\b(function|def|class|var|const|let|import|from|return|if|else|for|while)\b',
        r'[{}\[\]();=>]',
        r'[a-zA-Z_][a-zA-Z0-9_]*\([^\)]*\)',
        r'[\w_]+\.[a-zA-Z_]\w*',
        r'\.(py|js|ts|java|cpp|cs|php|rb|go|rs|swift|kt)\b',
        r'\b(api|sdk|npm|pip|docker|git|aws|azure|kubernetes|k8s)\b',
        r'```[\s\S]*```',
        r'`[^`]+`',
    ]
    combined_pattern = '|'.join(code_indicators)
    if re.search(combined_pattern, query, re.IGNORECASE):
        return True

    code_keywords = {
        'implement', 'debug', 'compile', 'runtime', 'error', 'exception',
        'function', 'method', 'class', 'object', 'variable', 'array',
        'database', 'query', 'api', 'endpoint', 'request', 'response',
        'server', 'client', 'framework', 'library', 'package', 'module'
    }
    query_words = set(query.lower().split())
    return len(query_words.intersection(code_keywords)) >= 2


def generate_query_refinement_prompt(
    query: str,
    mode: Literal["llm_only", "memory_llm", "web_memory_llm"] = "memory_llm",
    context: str = "",
    refined_query: str = "",
    title: str = "",
    description: str = ""
) -> str:
    """Generates a prompt for LLM to refine search queries for vector/semantic search.

    Args:
        query (str): The current user query to be refined
        mode (Literal): Operating mode - llm_only, memory_llm, or web_memory_llm
        context (str, optional): Chat history in user-assistant pairs. Defaults to "".
        refined_query (str, optional): Previous refined query terms. Defaults to "".
        title (str, optional): Related topic title. Defaults to "".
        description (str, optional): Additional context description. Defaults to "".

    Returns:
        str: Prompt instructing LLM to generate a refined query optimized for vector search.
    """

    is_code_query = detect_code_query(query)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt_addition_for_code = """
3. If code-related:
   - Preserve exact code related to query at start
   - Include programming context
   - Maintain framework/library mentions""" if is_code_query else ""

    mode_focus = {
        "llm_only": "Focus only on current query along with context, optimize for direct answers",
        "memory_llm": "Balance current query with chat history context",
        "web_memory_llm": "Optimize for web content while maintaining context"
    }

    prompt = f"""You are a query refinement system. Generate ONE refined search query optimized for vector and semantic search.

IMPORTANT: Return ONLY the refined query. No explanations, no metadata, no additional text. 
Current time: {current_time}

Example:
Input Query: "How do I add authentication to FastAPI?"
Chat Context: "Previously discussed FastAPI routing and middleware setup"
Refined Query: "authentication FastAPI"
Title: None
Description: None

BAD Response: "Here's a refined query: FastAPI authentication implementation guide"
GOOD Response: FastAPI authentication implementation OAuth2 JWT security middleware integration best practices

Input Query: {query}
Mode: {mode}
Previous Query Terms: {refined_query if refined_query else "None"}
Title: {title if title else "None"}
Description: {description if description else "None"}

Chat Context:
{context if context else "No previous context"}

Instructions:
1. Create ONE search query that:
   - Captures the core intent of the current query
   - Incorporates relevant context from chat history
   - Uses precise technical terms from discussion
   - Is optimized for vector similarity search
   - Contains 15-40 words depending on complexity

2. Mode-specific focus:
   - {mode_focus[mode]}

{prompt_addition_for_code}

REMEMBER: Like the GOOD example above, output ONLY the refined query without any other text."""

    return prompt.strip()
