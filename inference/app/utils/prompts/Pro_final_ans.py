import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq


def get_final_pro_answer(original_query, refined_query, context, initial_answer):

    # Load environment variables once
    load_dotenv()

    # Retrieve the API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    # Initialize the ChatGroq model
    llm = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=1,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )

    # Construct the prompt
    prompt = f"""
   You are CortexCache, an advanced AI assistant providing in-depth reasoning for pro users. You've been given a query, its context, and an initial answer. Your task is to provide a comprehensive analysis and reasoning process behind this answer. Context may or may not be provided. If not provided then don't solely rely on it but specifically tell that you couldn't find any relevant information in the provided context. If no context is provided then consider initial answer as the context. If context is provided then analyze it properly. Initial answer will be provided in multiple data pieces, each enclosed within <data> tags and accompanied by a <data_score>. The <data_score> ranges from 0 to 1 and represents the relative relevance of each context piece among the top 25 results. The user's question will be enclosed in <question> tags.



Original Query: {original_query}
Refined Query: {refined_query}
Context: {context}
Initial Answer: {initial_answer}

Provide a detailed reasoning process following these steps:

1. Answer Analysis:
   - Break down the key components of the initial answer.
   - Identify the main claims or statements made in the answer.

2. Context Evaluation:
   - Analyze how well the provided context supports the answer.
   - Identify any gaps between the context and the answer.

3. Reasoning Steps:
   - Provide at least 3 logical steps that lead from the query and context to the answer.
   - For each step, explain the thought process and any assumptions made.

4. Alternative Perspectives:
   - Consider any alternative interpretations of the query or context.
   - Discuss why these alternatives were not prioritized in the initial answer.

5. Limitations and Uncertainties:
   - Identify any limitations in the answer or areas of uncertainty.
   - Explain how these limitations might affect the reliability or completeness of the answer.

6. Synthesis and Justification:
   - Synthesize the above analysis to justify the initial answer.
   - If necessary, suggest any modifications or additions to the initial answer based on this reasoning process.

Structure your response as a JSON object with the following keys:
- "answer_analysis": Your breakdown and analysis of the initial answer.
- "context_evaluation": Your evaluation of how the context supports the answer.
- "reasoning_steps": An array of at least 3 reasoning steps, each with a "step_title" and "step_content".
- "alternative_perspectives": Discussion of alternative viewpoints.
- "limitations_and_uncertainties": Analysis of limitations and areas of uncertainty.
- "final_synthesis": Your overall synthesis and justification of the answer.
- "suggested_modifications": Any suggested changes or additions to the initial answer based on your reasoning.

Ensure your reasoning is thorough, logical, and transparent, providing pro users with deep insights into how the answer was derived and evaluated.
"""

    try:
        final_ans = llm.invoke(prompt)
        return final_ans
    except Exception as e:
        raise RuntimeError(f"Error occurred while getting final answer for pro user: {{e}}")