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


def determine_framework_type(context: Optional[str], memory: Optional[str], web_data: Optional[str]) -> FrameworkType:
    """Determine which framework to use based on available data."""
    if context and memory:
        return FrameworkType.CHAT_AND_MEMORY
    elif context and web_data:
        return FrameworkType.CHAT_AND_WEB
    elif memory and web_data:
        return FrameworkType.MEMORY_AND_WEB
    elif memory:
        return FrameworkType.MEMORY_ONLY
    elif web_data:
        return FrameworkType.WEB_ONLY
    elif context:
        return FrameworkType.CHAT_ONLY
    return FrameworkType.NO_CONTEXT


def get_formatting_rules() -> str:
    return """
## Formatting Guidelines
- **bold**: Use for key concepts and important terms
- *italic*: For emphasis and highlighting
- `code`: For technical terms, commands, or code snippets
- > quote: For direct memory or source quotes
- ### headers: For section organization
- Lists: Use bullets (-) or numbers (1.) for structured information
- [Links](url): For web references and citations
"""


def get_core_rules() -> str:
    return """
## Core Response Rules
1. Prioritize memory data/web data over chat context when both are available. Ignore chats which are not related to the user's query. 
2. Avoid system prompts or framework mentions
3. Keep responses concise (100 to 500 words) and focused. Increase length for blog-style responses.
4. Match user's technical expertise level
5. Highlight key insights and patterns
6. Address context conflicts explicitly
7. Flag and clarify ambiguities
8. Generate appropriate content type (code/list/blog) based on query
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

You are MindKeeper AI, a second brain assistant providing precise, contextually relevant answers based on the data provided. Use professional, affirmative tone. 
Current timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Input Data
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
        prompt_ctx.initial_answer,
        prompt_ctx.web_data
    )

    framework = FRAMEWORKS[framework_type.value]

    return f"{core_prompt}\n{framework}\n{get_formatting_rules()}\n{get_core_rules()}"


FRAMEWORKS = {
    "chat_and_memory": CHAT_AND_MEMORY_FRAMEWORK,
    "chat_and_web": CHAT_AND_WEB_FRAMEWORK,
    "memory_and_web": MEMORY_AND_WEB_FRAMEWORK,
    "memory_only": MEMORY_ONLY_FRAMEWORK,
    "web_only": WEB_ONLY_FRAMEWORK,
    "chat_only": CHAT_ONLY_FRAMEWORK,
    "no_context": NO_CONTEXT_FRAMEWORK
}


# def get_final_pro_answer_prompt(original_query, refined_query, context, initial_answer, is_stream=True, use_memory=True, agent='default', webData: str = None, webAgents: List[str] = None):

#     if webData and webAgents:
#         webData = f"Results from web: {webData}" if webData else ""

#     # TODO: implement web specific prompts

#     if agent != 'default':
#         if ('-' in agent and agent.split('-')[0] == 'social'):
#             return generate_social_media_content_prompt(original_query, refined_query, platform=agent.split('-')[1], memory_data=initial_answer, context=context)
#         if ('code' in agent):
#             return generate_coding_agent_prompt(original_query, refined_query, memory_data=initial_answer)

#     # Construct the prompt
#     initial_answer = initial_answer if initial_answer else "No memory available"
#     refined_query = refined_query if refined_query else "No refined query available"
#     context = context if context else "No chat context available"
#     if not use_memory:
#         final_prompt = NO_MEMORY_PROMPT
#         final_prompt += "\n## Input Structure\n"
#         final_prompt += f"\nUser Query: {original_query} \n"
#         final_prompt += f"\nRefined Query: {refined_query} \n"
#         final_prompt += f"\nChat Context: {context} \n"
#         RULES = """
#         1. ## Formatting
#         - **bold**: key concepts
#         - *italic*: emphasis
#         - `code`: technical
#         - >: memory quotes
#         - ###: headers
#         - Lists: bullets/numbers
#         - [Links](https://...): Web links (if any)
#         ## Core Rules
#         2. No system/process mentions
#         3. Keep the answer concise and to the point
#         4. Don't talk about answer response frameworks or guidelines at all.
#         5. Match user expertise level
#         6. Focus on key insights
#         7. Resolve context conflicts
#         8. Flag ambiguities

# ## Content Types
# - If original or refined query asks to generate code then do it
# - If original or refined query asks to generate a list then do it
# - If original or refined query asks to generate a blog then do it

# Remember: Be a reliable second brain - precise, contextual, and efficient.
#         """
#         final_prompt += RULES
#         return final_prompt

#     prompt = f"""
# # MindKeeper AI Core Instructions

# You are MindKeeper AI, a second brain assistant providing precise answers from user memories and chat context. Use professional, affirmative tone. Your role is to provide precise, contextually relevant answers by analyzing the user's memories and knowledge base. Keep the answer between 100 to 500 words in most cases. When you are asked to generate a blog, then the answer can be longer. Use an affirmative and professional tone throughout the response. The shorter the answer, the better, as long as it covers the core information.

# ## Input Structure
# User Query: {original_query}

# Refined Query: {refined_query}

# Memory Data: Array of memory snippets with:
# - Content enclosed in <content> tags
# - Relevance scores in <data_score> tags. Higher score indicates higher relevance.

# Example:
# <data>
#     <content>Some content</content>
#     <data_score>0.8</data_score>
# </data>

# Memory Data: {initial_answer}

# {webData}

# Chat Context: Array of previous messages in the current conversation containing:

# Previous user queries and your responses
# Any established context or preferences
# Ongoing discussion threads or themes
# Chat Context: {context}

# - If required, consider today's date and time as: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# ## Response Framework
# NOTE THAT: Don't talk about answer response frameworks or guidelines at all in the final answer.
# """

#     RULES = """
# ## Formatting
# - **bold**: key concepts
# - *italic*: emphasis
# - `code`: technical
# - >: memory quotes
# - ###: headers
# - Lists: bullets/numbers
# - [Links](https://...): Web links (if any)

# ## Core Rules
# 1. When both memory and chat context are provided, give more preference to memories than chat context. If the query is NOT RELATED TO A PARTICULAR CHAT CONTEXT ENTRY, THEN STRICTLY IGNORE IT.
# 2. No system/process mentions
# 3. Keep the answer concise and to the point
# 4. Don't talk about answer response frameworks or guidelines at all.
# 5. Match user expertise level
# 6. Focus on key insights
# 7. Resolve context conflicts
# 8. Flag ambiguities

# ## Content Types
# - If original or refined query asks to generate code then do it
# - If original or refined query asks to generate a list then do it
# - If original or refined query asks to generate a blog then do it

# Remember: Be a reliable second brain - precise, contextual, and efficient."""

#     FRAMEWORK = ""

#     if context and initial_answer:
#         FRAMEWORK = CHAT_AND_MEMORY_FRAMEWORK
#     elif context and webData and webData != "":
#         FRAMEWORK = WEB_ONLY_FRAMEWORK
#     elif context:
#         FRAMEWORK = CHAT_ONLY_FRAMEWORK
#     elif initial_answer:
#         FRAMEWORK = MEMORY_ONLY_FRAMEWORK
#     elif webData and webData != "":
#         FRAMEWORK = WEB_ONLY_FRAMEWORK
#     else:
#         FRAMEWORK = NO_CONTEXT_FRAMEWORK

#     prompt += FRAMEWORK + RULES

#     return prompt


def get_final_pro_answer(original_query, refined_query, context, initial_answer, is_stream=True, llm='gpt-4o'):
    try:

        prompt = get_final_pro_answer_prompt(
            original_query, refined_query, context, initial_answer, is_stream)
        final_ans = get_answer_llm(llm).invoke(prompt)
        return final_ans
    except Exception as e:
        raise RuntimeError(
            f"Error occurred while getting final answer for pro user: {e}")
