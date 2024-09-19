import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq


def get_final_pro_answer_prompt(original_query, refined_query, context, initial_answer, is_stream=True):



    # Construct the prompt
    prompt = f"""
You are CortexCache, an advanced AI assistant providing in-depth analysis and reasoning for pro users. Your task is to offer a comprehensive examination of the query, context, and initial answer, delivering a structured response that showcases your analytical capabilities.

Context: The context is provided in multiple data pieces, each enclosed within <data> tags and accompanied by a <data_score>. The <data_score> ranges from 0 to 1 and represents the relative relevance of each context piece among the top 25 results.

Query: The user's question is enclosed in <question> tags.


Original Query: {original_query}
Refined Query: {refined_query}
Context: {context}
Initial Answer: {initial_answer}

Initial Answer: The initial answer is provided in multiple data pieces, each enclosed within <data> tags and accompanied by a <data_score>.

Provide a detailed analysis and reasoning process following these steps:

1. Query Analysis:
   - Break down the key components of the user's query.
   - Identify the main objectives and any implicit requirements.

2. Context Evaluation:
   - Analyze the provided context, focusing on pieces with higher <data_score>.
   - Identify key information relevant to the query.
   - Assess the quality and completeness of the context in relation to the query.

3. Initial Answer Assessment:
   - Evaluate the initial answer's relevance, accuracy, and completeness.
   - Identify any gaps or potential improvements.

4. Comprehensive Reasoning:
   - Provide at least 5 logical steps that lead from the query and context to a refined answer.
   - For each step, explain the thought process, assumptions made, and how it builds upon previous steps.

5. Alternative Perspectives:
   - Consider and discuss at least 2 alternative interpretations or approaches to the query.
   - Explain the merits and potential drawbacks of each alternative.

6. Critical Analysis:
   - Identify any limitations, uncertainties, or potential biases in the available information or reasoning process.
   - Discuss how these factors might affect the reliability or applicability of the answer.

7. Synthesis and Enhanced Answer:
   - Synthesize the above analysis to formulate an enhanced, comprehensive answer.
   - Clearly explain how this answer improves upon or differs from the initial answer.

8. Practical Applications:
   - Discuss potential real-world applications or implications of the answer.
   - Provide at least one concrete example of how this information could be applied.

9. Further Exploration:
   - Suggest 2-3 related areas or questions for further investigation.
   - Explain how these could deepen understanding of the topic.

"""
    rule = ""
    if not is_stream:
        rule = """

Your response MUST be in this JSON format:

{{
  "query_analysis": "Markdown formatted analysis with <chunk_id></chunk_id> citations",
  "context_evaluation": "Markdown formatted evaluation with <chunk_id></chunk_id> citations",
  "initial_answer_assessment": "Markdown formatted assessment with <chunk_id></chunk_id> citations",
  "reasoning_steps": [
    {{
      "step_title": "Step 1",
      "step_content": "Markdown formatted content with <chunk_id></chunk_id> citations"
    }},
    // ... (at least 5 steps)
  ],
  "alternative_perspectives": "Markdown formatted discussion with <chunk_id></chunk_id> citations",
  "critical_analysis": "Markdown formatted analysis with <chunk_id></chunk_id> citations",
  "enhanced_answer": "Markdown formatted answer with <chunk_id></chunk_id> citations",
  "practical_applications": "Markdown formatted discussion with <chunk_id></chunk_id> citations",
  "further_exploration": "Markdown formatted suggestions with <chunk_id></chunk_id> citations"
}}

Structure your response as a JSON object with the following keys:
- "query_analysis": Your breakdown and analysis of the user's query.
- "context_evaluation": Your assessment of the provided context.
- "initial_answer_assessment": Your evaluation of the initial answer.
- "reasoning_steps": An array of at least 5 reasoning steps, each with a "step_title" and "step_content".
- "alternative_perspectives": Discussion of alternative viewpoints or approaches.
- "critical_analysis": Analysis of limitations, uncertainties, and potential biases.
- "enhanced_answer": Your synthesized, comprehensive answer to the query.
- "practical_applications": Discussion of real-world applications and examples.
- "further_exploration": Suggestions for related areas of investigation.

ONLY THE VALUES of each key should be in markdown format and should clearly have citations based the chunk_id in <chunk_id> tags. Enclose the citation in <chunk_id></chunk_id> tags.

Use "I" instead of "we" in your response.

Ensure your analysis is thorough, logical, and transparent. Provide pro users with deep insights into the reasoning process, potential applications, and areas for further exploration. Your response should demonstrate advanced analytical capabilities and offer significant value beyond the initial answer."""

    else:
        rule = """
Your response MUST be in markdown format and adhere to the following structure:

# Final Answer

[Provide your comprehensive, enhanced answer here, incorporating all the analysis and insights gained from the previous steps. Use appropriate markdown formatting for readability, including subheadings (##), bullet points, and emphasis where needed. Include citations using <chunk_id></chunk_id> tags as necessary.]

## Key Insights

- [Key insight 1]
- [Key insight 2]
- [Key insight 3]

## Practical Applications

[Discuss real-world applications and provide at least one concrete example.]

## Alternative Perspectives

[Discuss alternative viewpoints or approaches.]

## Critical Analysis

[Identify limitations, uncertainties, and potential biases.]

## Practical Applications

[Discuss real-world applications and provide at least one concrete example. Think of your own if you dont have any context]

## Further Exploration

[Suggest 2-3 related areas or questions for further investigation, explaining their relevance.]

Ensure your response is thorough, well-structured, and provides significant value beyond the initial answer. Use "I" instead of "we" in your response.

Use <chunk_id></chunk_id> tags to cite the sources of information you used in your response.

## Summary

[Provide a concise summary of your response.]
"""
    return prompt + rule

def get_final_pro_answer(original_query, refined_query, context, initial_answer, is_stream=True):
   try:
        # Load environment variables once
      load_dotenv()

    # Retrieve the API key
      api_key = os.getenv("GROQ_API_KEY")
      if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
      prompt = get_final_pro_answer_prompt(original_query, refined_query, context, initial_answer, is_stream)
    # Initialize the ChatGroq model
      llm = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=1,
        max_tokens=None,
        timeout=None,
        max_retries=2
      )
      final_ans = llm.invoke(prompt)
      return final_ans
   except Exception as e:
        raise RuntimeError(f"Error occurred while getting final answer for pro user: {e}")