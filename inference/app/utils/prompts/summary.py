from app.utils.llms import summary_llm as llm


def get_summary(context: str):
    prompt = f"""
    You are a precise conversation summarizer for an AI assistant. Summarize the conversation history, focusing more on the recent user-AI interactions. Specifically catch details regarding what user is or attaches something to your or its own identity. Your summary must not exceed 150 words. Follow these guidelines:

1. Analyze the 5 most recent user-AI conversation pairs.
2. Identify the main topic and any subtopics discussed.
3. Track changes in the user's queries or focus.
4. Highlight significant context shifts or new information introduced.
5. Note any specific examples or personal details shared by the user.
6. Capture key points from the AI's responses.

Use this structure for your summary:

## Initial Topic (10-15 words)
[Briefly state the starting point of the conversation within the 5 pairs]

## Key Points (30-40 words)
- [List 2-3 main points discussed]

## Query Evolution (30-40 words)
- [Note how the user's focus changed]

## Current Focus (20-25 words)
[Summarize the most recent query or topic]

## Important Context (30-40 words)
- [List 1-2 crucial details that might influence future responses]

Note that total word count should strictly be within 150 words. Avoid repeating information or including irrelevant details. Provide a concise and informative summary.
User's context with user and AI chats:    {context}"""
    summary = llm.invoke(prompt)
    return summary