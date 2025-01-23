from datetime import datetime
from typing import List, Optional

# from app.utils.llms import answer_llm_pro as llm
from app.schemas.prompt_context import FrameworkType, PromptContext
from app.utils.llms import get_answer_llm
from app.utils.prompts.agents.CodingAgent import generate_coding_agent_prompt
from app.utils.prompts.agents.SocialMedia import \
    generate_social_media_content_prompt
from app.utils.prompts.frameworks import (CHAT_AND_MEMORY_FRAMEWORK,
                                          CHAT_AND_WEB_FRAMEWORK,
                                          CHAT_ONLY_FRAMEWORK,
                                          MEMORY_AND_WEB_FRAMEWORK,
                                          MEMORY_ONLY_FRAMEWORK,
                                          NO_CONTEXT_FRAMEWORK,
                                          WEB_ONLY_FRAMEWORK)


def determine_framework_type(context: Optional[str], use_memory: bool, web_data: Optional[str], total_memories) -> FrameworkType:
    """Determine which framework to use based on available data."""
    if context and len(context) == 0:
        context = None
    if not use_memory or total_memories == 0:
        use_memory = False
    if web_data and len(web_data) == 0:
        web_data = None

    if context and use_memory:
        return FrameworkType.CHAT_AND_MEMORY
    elif context and web_data:
        return FrameworkType.CHAT_AND_WEB
    elif use_memory and web_data:
        return FrameworkType.MEMORY_AND_WEB
    elif use_memory:
        return FrameworkType.MEMORY_ONLY
    elif web_data:
        return FrameworkType.WEB_ONLY
    elif context:
        return FrameworkType.CHAT_ONLY
    return FrameworkType.NO_CONTEXT


def get_formatting_rules() -> str:
    return """
Ensure that your response has the contents present in all the memories of memory data as long as it is valid. Always includes top 3 memory items and top 3 web items if available. If not available, DON'T mention it.

## Formatting Guidelines

1. Text Formatting:
   - **bold**: For key technical terms, critical concepts, important metrics
   - *italic*: For definitions, new concepts, emphasis
   - `code`: For commands, functions, paths, variables, config values

2. Structure:
   - ### Headers: Use for main sections (### only)
   - #### Subheaders: For subsections
   - Keep headers brief (3-5 words)

3. Quotes & Citations:
   - > quote: Only for direct evidence (relevance > 0.7)
   - Use [cite:id] format for references

4. Lists:
   - Bullets (-): For unordered, parallel items
   - Numbers (1.): For sequential steps, priorities
"""


def get_citation_rules() -> str:
    return """
## Citation Guidelines
- Always provide proper citations for external sources
- Following the content, enclose the id of the source in square brackets prefixed with 'cite:'
- If there are multiple citations, use a comma and space to separate them

Example1: AI is important for the future [cite:1]
Example2: AI is important for the future [cite:1], [cite:2] and NOT AS [cite:1, cite:2]. STRICTLY FOLLOW THIS FORMAT.
"""


def get_core_rules() -> str:
    return """
# Core Response Rules
0. Never add headings like "Answer:". Begin as framework specifies.

1. Data Handling (3 Requirements):
   - Prefer provided data over general knowledge
   - Strictly include all terms, especially tech/legal or those that start with capital letters as long as they are valid
   - Mandatory coverage: 
     1. Tech/data collection [cite]
     2. Third-party sharing [cite] 
     3. Legal exceptions [cite]
   - Validate citations match <id> tags first

2. Response Structure (3 Pillars):
   a) Facts: Direct quotes + tech details
   b) Implications: Risks/contradictions
   c) Actions: User steps + settings

3. Quality Enforcement:
   - Pre-output check: 
     1. All [cite] match existing IDs
     2. Tech+legal aspects addressed
     3. No unsupported claims
   - Quote key clauses verbatim [>0.7]
   - If missing info: "No [category] found"

4. Efficiency Rules:
   - Max 5 bullet points per section
   - Combine related concepts (e.g., "tech/data collection")
   - Use abbreviations: tech=technical, implications=impacts
   - Avoid explanations of rules - direct commands only
"""


def get_final_pro_answer_prompt(prompt_ctx: PromptContext) -> str:
    """
  Generate the final prompt based on context and available data.

   Args:
        prompt_ctx: PromptContext containing all necessary prompt information

    Returns:
        str: Formatted prompt for the LLM
    """
    # Handle special agent types first
    if prompt_ctx.agent != 'default':
        if prompt_ctx.agent.startswith('social-'):
            platform = prompt_ctx.agent.split('-')[1]
            return generate_social_media_content_prompt(
                prompt_ctx.original_query,
                prompt_ctx.refined_query,
                platform=platform,
                memory_data=prompt_ctx.initial_answer,
                context=prompt_ctx.context
            )
        elif 'code' in prompt_ctx.agent:
            return generate_coding_agent_prompt(
                prompt_ctx.original_query,
                prompt_ctx.refined_query,
                memory_data=prompt_ctx.initial_answer
            )

    # Construct main prompt
    core_prompt = f"""
# MindKeeper AI

You are MindKeeper AI, a second brain assistant providing precise, contextually relevant answers based on the data provided. Use professional, affirmative tone. You are expert at giving responses involving technical terms and contexts based on the data provided.

# What is MindKeeper AI?
MindKeeper AI is a cutting-edge personal knowledge management tool designed to function as a user's second brain. It allows users to upload a wide range of content, including screenshots, videos, web links, YouTube videos, public Git repositories, Notion pages, and Google Drive files. This content is securely encrypted and stored, enabling users to query the app in natural language and receive precise answers with proper citations.

Current timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# Input Data
User Query: {prompt_ctx.original_query}
Refined Query: {prompt_ctx.refined_query or "No refined query available"}


Context data can be of 2 types: Memory Data and Web Data. It is of the format:
- Content enclosed in <content> tags
- Relevance scores in <data_score> tags. Higher score indicates higher relevance. Give preference to higher scores irrespective of the type.

Memory Data: {prompt_ctx.initial_answer or "No memory available"}
{f"Web Data: {prompt_ctx.web_data}" if prompt_ctx.web_data else "No web data available"}
Chat Context: {prompt_ctx.context or "No chat context available"}
"""

    # Determine and add appropriate framework
    framework_type = determine_framework_type(
        prompt_ctx.context,
        prompt_ctx.use_memory,
        prompt_ctx.web_data,
        prompt_ctx.total_memories
    )

    framework = FRAMEWORKS[framework_type.value]

    return f"{core_prompt}\n{framework}\n{get_formatting_rules()}\n{get_citation_rules()}\n{get_core_rules()}"


FRAMEWORKS = {
    "chat_and_memory": CHAT_AND_MEMORY_FRAMEWORK,
    "chat_and_web": CHAT_AND_WEB_FRAMEWORK,
    "memory_and_web": MEMORY_AND_WEB_FRAMEWORK,
    "memory_only": MEMORY_ONLY_FRAMEWORK,
    "web_only": WEB_ONLY_FRAMEWORK,
    "chat_only": CHAT_ONLY_FRAMEWORK,
    "no_context": NO_CONTEXT_FRAMEWORK
}


def get_final_pro_answer(original_query, refined_query, context, initial_answer, is_stream=True, llm='gpt-4o'):
    try:

        prompt = get_final_pro_answer_prompt(
            original_query, refined_query, context, initial_answer, is_stream)
        final_ans = get_answer_llm(llm).invoke(prompt)
        return final_ans
    except Exception as e:
        raise RuntimeError(
            f"Error occurred while getting final answer for pro user: {e}")
