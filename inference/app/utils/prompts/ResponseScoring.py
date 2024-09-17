def scoring_prompt(original_query, refined_query, context, answer_1, answer_2, answer_3, answer_4, answer_5):
    prompt = f"""
You are an expert evaluator tasked with analyzing and ranking 5 AI-generated answers to a user query. Your goal is to provide a comprehensive comparison and ranking of these answers.

Original Query: {original_query}

Refined Query: {refined_query}

Context: {context}
For each answer, evaluate based on the following criteria:
1. Relevance (0-10): How directly does it address the original query?
2. Comprehensiveness (0-10): How thorough and complete is the answer?
3. Context Utilization (0-10): How well does it use the provided high-scoring context?
4. Clarity and Structure (0-10): How well-organized and easy to understand is the answer?
5. Source Citation (0-5): Does it properly cite sources from the context?

After evaluating all answers, rank them based on their total scores and provide a comparative analysis.

Answer 1:
{answer_1}

Answer 2:
{answer_2}

Answer 3:
{answer_3}

Answer 4:
{answer_4}

Answer 5:
{answer_5}

Provide your evaluation and analysis in the following strictly in the following JSON format:

{{
 "ranked_answers": [
    {{
      \"rank\": 1,
      \"original_index\": 0,
      \"content\": \"Full content of the highest-scoring answer\",
      \"scores\": {{
        \"relevance\": 0,
        \"comprehensiveness\": 0,
        \"context_utilization\": 0,
        \"clarity_structure\": 0,
        \"source_citation\": 0
      }},
      \"total_score\": 0,
      \"key_strengths\": \"Brief description of what makes this answer stand out\",
      \"areas_for_improvement\": \"Any aspects where this answer could be better\"
    }},
    {{
      \"rank\": 2,
      \"original_index\": 0,
      \"content\": \"Full content of the second-highest scoring answer\",
      \"scores\": {{
        \"relevance\": 0,
        \"comprehensiveness\": 0,
        \"context_utilization\": 0,
        \"clarity_structure\": 0,
        \"source_citation\": 0
      }},
      \"total_score\": 0,
      \"key_strengths\": \"Brief description of what makes this answer strong\",
      \"areas_for_improvement\": \"Any aspects where this answer could be better\",
      \"key_difference\": \"What this answer provides that the top answer doesn't\"
    }},
    // Repeat this structure for ranks 3, 4, and 5
  ],
  \"comparative_analysis\": \"A brief overall analysis comparing the strengths and weaknesses of all 5 answers, highlighting key differences and explaining the ranking rationale\",
  \"recommendation\": \"A concise recommendation on which answer(s) might be most useful to the user and why\"
}}
"""

    return prompt
