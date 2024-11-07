import re
from typing import Dict, List, Optional


def create_coding_agent_prompt(
    original_query: str,
    refined_query: str,
    memory_data: str = None
) -> str:
    """
    Creates a prompt for code generation based on query and available memory
    """

    # Extract programming language from query
    def extract_language(query: str) -> str:
        # Common programming language patterns
        languages = {
            'python': r'\b(python|py)\b',
            'javascript': r'\b(javascript|js|node\.?js)\b',
            'typescript': r'\b(typescript|ts)\b',
            'java': r'\b(java)\b',
            'c++': r'\b(c\+\+|cpp)\b',
            'c#': r'\b(c#|csharp)\b',
            'ruby': r'\b(ruby|rb)\b',
            'go': r'\b(golang|go)\b',
            'rust': r'\b(rust|rs)\b',
            'php': r'\b(php)\b',
            'swift': r'\b(swift)\b',
            'kotlin': r'\b(kotlin|kt)\b',
            'r': r'\b(r programming|r language|\br\b)\b',
            'sql': r'\b(sql|mysql|postgresql|sqlite)\b'
        }

        combined_query = f"{original_query} {refined_query}".lower()

        for lang, pattern in languages.items():
            if re.search(pattern, combined_query, re.IGNORECASE):
                return lang

        return "unspecified"

    detected_language = extract_language(original_query + " " + refined_query)

    base_prompt = """
    You are a Code Generation Agent, a specialized component of MindKeeper AI. Your purpose is to generate high-quality, production-ready code that follows best practices, includes proper documentation, and implements robust error handling.

    ## Request Details
    Original Query: {original_query}
    Refined Query: {refined_query}
    Detected Language: {language}

    ## Code Generation Standards
    1. Code Quality Requirements:
       - Clean, readable, and maintainable code
       - Proper error handling and edge cases
       - Memory and performance optimization
       - Security best practices
       - Appropriate logging
       - Unit test coverage
       - Clear documentation
       - Type hints (where applicable)
       - Consistent code style
       - Design patterns (when relevant)

    2. Documentation Requirements:
       - Detailed function/class descriptions
       - Parameter explanations
       - Return value specifications
       - Usage examples
       - Edge case handling
       - Dependencies and requirements
       - Setup instructions
       - Performance considerations
    """

    memory_based_prompt = base_prompt + """
    ## Memory Context Available
    Using provided memory data to enhance and customize code generation.

    Memory Data Format:
    <data>
        <content>Code/logic snippet</content>
        <data_score>Relevance score (0-1)</data_score>
    </data>

    Memory Data: {memory_data}

    ## Generation Guidelines
    1. Analyze memories for:
       - Existing code patterns
       - Architectural decisions
       - Previous solutions
       - Known constraints
       - Testing approaches
       - Performance requirements

    2. Generate code that:
       - Maintains consistency with existing codebase
       - Follows established patterns
       - Integrates with existing solutions
       - Addresses known issues
       - Builds upon successful approaches

    ## Output Structure
    1. Code Implementation
       - Complete, runnable code
       - Inline comments
       - Error handling
       - Logging
       - Type hints

    2. Documentation
       - Usage examples
       - Integration notes
       - Memory context references
       - Performance considerations

    3. Testing
       - Unit tests
       - Edge case coverage
       - Integration test examples

    4. Additional Notes
       - Memory-specific considerations
       - Integration guidelines
       - Scaling considerations
    """

    no_memory_prompt = base_prompt + """
    ## No Memory Context
    Generating code based on industry best practices and standard patterns.

    ## Generation Guidelines
    1. Focus on:
       - Universal design patterns
       - Industry best practices
       - Standard libraries
       - Common use cases
       - Proven architectures

    2. Generate code that:
       - Follows language conventions
       - Uses standard libraries effectively
       - Implements common patterns
       - Provides flexibility
       - Maintains scalability

    ## Output Structure
    1. Code Implementation
       - Complete, runnable code
       - Inline comments
       - Error handling
       - Logging
       - Type hints

    2. Documentation
       - Setup instructions
       - Usage examples
       - API documentation
       - Performance notes

    3. Testing
       - Unit tests
       - Common edge cases
       - Integration examples

    4. Additional Notes
       - Scaling considerations
       - Alternative approaches
       - Extension points
    """

    # Add language-specific guidelines based on detected language
    language_guidelines = {
        "python": """
        Python-Specific Guidelines:
        - Follow PEP 8 style guide
        - Use type hints (Python 3.6+)
        - Implement context managers when appropriate
        - Utilize list comprehensions judiciously
        - Leverage standard library tools
        - Consider async/await for I/O operations
        - Use pathlib for file operations
        - Implement proper package structure
        """,

        "javascript": """
        JavaScript/Node.js Guidelines:
        - Use ES6+ features appropriately
        - Implement proper async/await patterns
        - Consider browser compatibility
        - Follow npm package structure
        - Implement proper error handling
        - Use appropriate bundling tools
        - Consider memory management
        - Implement proper security measures
        """,

        "typescript": """
        TypeScript Guidelines:
        - Utilize strict type checking
        - Implement interfaces and types
        - Use generics when appropriate
        - Follow TSLint/ESLint rules
        - Implement proper type guards
        - Use utility types effectively
        - Consider compile-time optimizations
        - Maintain type safety
        """
    }

    # Select appropriate base prompt
    selected_prompt = memory_based_prompt if memory_data else no_memory_prompt

    # Add language-specific guidelines if available
    if detected_language in language_guidelines:
        selected_prompt += "\n" + language_guidelines[detected_language]

    # Format the prompt with provided data
    formatted_prompt = selected_prompt.format(
        original_query=original_query,
        refined_query=refined_query,
        language=detected_language,
        memory_data=memory_data if memory_data else "None provided"
    )

    return formatted_prompt


def generate_coding_agent_prompt(
    query: str,
    refined_query: str,
    memory_data: str = None
) -> str:
    """
    Generate code using the appropriate prompt
    """
    prompt = create_coding_agent_prompt(
        original_query=query,
        refined_query=refined_query,
        memory_data=memory_data
    )

    return prompt
