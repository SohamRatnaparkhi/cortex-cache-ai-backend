from datetime import datetime
from typing import Dict, List, Optional


def create_social_media_agent_prompt(
    original_query: str,
    refined_query: str,
    memory_data: Optional[List[Dict]] = None,
    platform: str = "all",
    context: str = ""
) -> str:
    """
    Creates a prompt for social media content generation based on whether memory data is available
    """

    base_prompt = """
    You are a Social Media Content Generation Agent, an extension of MindKeeper AI. Your primary role is to create engaging, platform-optimized social media content that maintains brand voice and drives engagement. Generate content that is authentic, engaging, and aligned with the platform's best practices.

    ## User Request
    Original Query: {original_query}
    Refined Query: {refined_query}
    Target Platform: {platform}
    Chat context: {context}
    Date and time: {date}
    """

    with_memory_prompt = base_prompt + """
    ## Memory Context Available
    Working with user's stored memories and knowledge to create personalized content.

    Memory Data Format:
    <data>
        <content>Content snippet</content>
        <data_score>Relevance score (0-1)</data_score>
    </data>

    Memory Data: {memory_data}

    ## Content Generation Guidelines
    1. Analyze provided memories for:
       - Key themes and insights
       - Unique perspectives
       - Successful past content patterns
       - User's tone and style
       - Historical engagement data (if provided else ignore)

    2. Create platform-specific content that:
       - Incorporates insights from memories
       - Maintains consistent brand voice
       - Leverages proven successful formats
       - References relevant past experiences
       - Builds on existing narrative

    ## Output Format
    For each content piece, provide:
    1. Platform-specific post
    2. Hashtag recommendations
    3. Best posting time based on memory patterns
    4. Engagement strategy
    5. Reference to supporting memory data

    Remember:
    - Maintain authenticity by properly contextualizing memories
    - Adapt tone for each platform while keeping core message
    - Suggest variations for A/B testing
    - Include calls-to-action based on historical engagement
    """

    no_memory_prompt = base_prompt + """
    ## No Memory Context
    Creating fresh content based on industry best practices and platform standards.

    ## Content Generation Guidelines
    1. Focus on:
       - Universal content principles
       - Platform-specific best practices
       - Current trends and formats
       - Engagement optimization
       - Brand voice development

    2. Create platform-specific content that:
       - Follows platform conventions
       - Encourages engagement
       - Uses proven formats
       - Incorporates trending elements
       - Maintains professional standards

    ## Output Format
    For each content piece, provide:
    1. Platform-specific post
    2. Hashtag recommendations
    3. Recommended posting time based on general best practices
    4. Engagement strategy
    5. Rationale for content choices

    Remember:
    - Follow platform-specific best practices
    - Include relevant trending topics
    - Optimize for maximum engagement
    - Maintain professional tone
    - Suggest testing variations
    """

    # Platform-specific guidelines
    platform_guidelines = {
        "twitter": """
        Twitter Specifications:
        - Character limit: 280
        - Optimal hashtags: 1-2
        - Best practices:
          * Use clear, concise language
          * Include call-to-action
          * Consider thread format for longer content
        """,

        "linkedin": """
        LinkedIn Specifications:
        - Professional tone
        - Optimal post length: 1300 characters
        - Best practices:
          * Include industry insights
          * Use professional formatting
          * Focus on business value
        """,

        "instagram": """
        Instagram Specifications:
        - Visual focus
        - Optimal hashtags: 8-15
        - Best practices:
          * Strong visual description
          * Story-driven captions
          * Engaging first line
        """,

        "facebook": """
        Facebook Specifications:
        - Optimal length: 100-250 characters
        - Best practices:
          * Emotion-driven content
          * Question-based engagement
          * Native video preference
        """
    }

    # Select appropriate base prompt
    selected_prompt = with_memory_prompt if memory_data else no_memory_prompt

    # Add platform-specific guidelines if a specific platform is requested
    if platform.lower() in platform_guidelines:
        selected_prompt += "\n" + platform_guidelines[platform.lower()]

    # Format the prompt with provided data
    formatted_prompt = selected_prompt.format(
        original_query=original_query,
        refined_query=refined_query,
        platform=platform,
        memory_data=memory_data if memory_data else "None provided",
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        context=context
    )

    return formatted_prompt

# Example usage


def generate_social_media_content_prompt(
    query: str,
    refined_query: str,
    platform: str = "all",
    memory_data: Optional[List[Dict]] = None,
    context: str = ""
) -> str:
    """
    Generate social media content using the appropriate prompt
    """
    prompt = create_social_media_agent_prompt(
        original_query=query,
        refined_query=refined_query,
        memory_data=memory_data,
        platform=platform,
        context=context
    )
    return prompt
