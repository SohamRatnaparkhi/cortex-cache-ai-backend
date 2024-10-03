from app.utils.llms import summary_llm as llm


def get_summary(context: str):
    prompt = f"""
You are a precise conversation summarizer for an AI assistant. Summarize the conversation history in 150 words or less, focusing on recent user-AI interactions and any details the user attaches to their identity. Follow these guidelines:
1. Analyze the conversation pairs in provided context.
2. Identify the main topic and key subtopics.
3. Track changes in the user's queries or focus.
4. Note any specific examples or personal details shared by the user.
5. Capture essential points from the AI's responses.

Use this structure:
## Initial Topic (1-2 sentences)
## Key Points (2-3 bullet points)
## Query Evolution (1-2 sentences)
## Current Focus (1 sentence)
## Important Context (1-2 bullet points)

Strictly adhere to the 150-word limit. Prioritize recent interactions and user-specific information. Avoid repetition and irrelevant details. Provide a concise and informative summary.
User's context with user and AI chats: {context}"""
    summary = llm.invoke(prompt)
    return summary
