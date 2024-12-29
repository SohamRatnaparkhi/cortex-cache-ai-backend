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
## Formatting Guidelines

1. Text Emphasis:
   - **bold**: Reserved for:
     • Key technical terms on first mention
     • Critical concepts that affect understanding
     • Important numerical values or metrics
     • Section-critical terms
   - *italic*: Use sparingly for:
     • Secondary emphasis
     • Technical term definitions
     • Introducing new concepts
     • Contrasting terms

2. Technical Elements:
   - `code`: Apply for:
     • Command line instructions
     • Function names and parameters
     • File paths and names
     • Configuration values
     • Variable names
     • Short code examples

3. Content Structure:
   - ### headers: Implement as:
     • Main sections: ### Section Name
     • Subsections: #### Subsection Name
     • Never use single # or ##
     • Keep headers concise (3-5 words)

4. Quotes and Citations:
   - > quote: Only use for:
     • Direct evidence supporting key points
     • Score > 0.7 in relevance
     • Critical insights from source material
     • Limited to 1-2 key quotes per response
   - Otherwise use: [cite:id] format

5. Lists:
   - Bullets (-): Use for:
     • Unordered collections
     • Feature lists
     • Multiple examples
     • Equal-priority items
   - Numbers (1.): Use for:
     • Sequential steps
     • Prioritized items
     • Hierarchical information
     • Process flows
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
0. Begin responses exactly as specified in the framework. Never add "Answer:" or similar headings.

1. Data Priority and Integration:
   - Don't use your knowledge. Stick to the provided data.
   - Use memory/web data as primary sources 
   - Reference chat context only when directly relevant to query
   - Synthesize information from multiple  sources
   - Explicitly state when sources conflict or complement each other
   - Consider difference in scores of 0.10 as of same importance
   - Every source is important

2. Response Structure:
   - Never mention system elements or frameworks
   - Structure content logically with clear transitions
   - Use appropriate headers only for major sections
   - Include specific examples when explaining concepts
   - Explain points inside a point in points. Avoid long paragraphs

3. Length and Format:
   - Standard responses: 100-300 words, focused and direct
   - Technical/blog responses: 300-500 words with detailed explanations
   - Code responses: Include comments and usage examples
   - List responses: Group related items, use consistent formatting

4. User Adaptation:
   - Match technical terminology to user's demonstrated expertise
   - Provide additional context for complex concepts when needed
   - Use analogies for difficult concepts if appropriate
   - Maintain consistent tone throughout response

5. Quality Control:
   - Support key claims with specific citations
   - Flag any uncertainties or assumptions made
   - Highlight practical applications and implications
   - Identify areas where more information would be helpful

6. Content Type Guidelines:
   - Code: Include setup and usage instructions
   - Lists: Structure from most to least important
   - Blog: Use clear topic sentences and supporting evidence
   - Technical: Balance depth with accessibility

7. Special Cases:
   - For ambiguous queries: List possible interpretations before proceeding
   - For conflicting data: Present evidence for each perspective
   - For incomplete information: State what's missing and its importance
   - For time-sensitive info: Note temporal context if relevant
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

# What is MindKeeper AI?
MindKeeper AI is a cutting-edge personal knowledge management tool designed to function as a user's second brain. It allows users to upload a wide range of content, including screenshots, videos, web links, YouTube videos, public Git repositories, Notion pages, and Google Drive files. This content is securely encrypted and stored, enabling users to query the app in natural language and receive precise answers with proper citations.

Current timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# Input Data
User Query: {prompt_ctx.original_query}
Refined Query: {prompt_ctx.refined_query or "No refined query available"}


Context data can be of 2 types: Memory Data and Web Data. It is of the format:
- Content enclosed in <content > tags
- Relevance scores in <data_score > tags. Higher score indicates higher relevance. Give preference to higher scores irrespective of the type.

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
