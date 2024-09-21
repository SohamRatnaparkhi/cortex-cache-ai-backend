import asyncio
import json
import time
from typing import Any, Dict, List, Tuple

from app.services.query import get_final_answer


async def generate_step(messages: List[Dict[str, str]]) -> Tuple[Dict[str, Any], float]:
    start_time = time.time()
    step_data = await get_final_answer(messages)
    thinking_time = time.time() - start_time
    return step_data, thinking_time

async def generate_response(prompt: str) -> Tuple[List[Tuple[str, str, float]], float]:
    system_message = """You are an expert AI assistant that explains your reasoning step by step. For each step, provide a title that describes what you're doing in that step, along with the content. Decide if you need another step or if you're ready to give the final answer. Respond in JSON format with 'title', 'content', and 'next_action' (either 'continue' or 'final_answer') keys. Use at least 3 reasoning steps. Be aware of your limitations as an LLM. Include exploration of alternative answers. Consider you may be wrong, and if so, where. Fully test all other possibilities. When re-examining, use a different approach. Use at least 3 methods to derive the answer. Use best practices. For the final answer, provide a comprehensive and detailed explanation."""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    
    steps = []
    step_count = 1
    total_thinking_time = 0
    
    while True:
        step_data, thinking_time = await generate_step(messages)
        total_thinking_time += thinking_time
        
        step_title = f"Step {step_count}: {step_data.get('title', 'No Title')}"
        step_content = step_data.get('content', 'No Content')
        steps.append((step_title, step_content, thinking_time))
        
        messages.append({"role": "assistant", "content": json.dumps(step_data)})
        
        if step_data.get('next_action') == 'final_answer':
            break
        
        step_count += 1

    messages.append({"role": "user", "content": "Please provide a comprehensive final answer based on your reasoning above. Include all relevant details and ensure the explanation is thorough and complete."})
    final_data, thinking_time = await generate_step(messages)
    total_thinking_time += thinking_time
    
    steps.append(("Final Answer", final_data.get('content', 'No Content'), thinking_time))
    
    return steps, total_thinking_time

# Usage
async def main():
    prompt = "What are the potential long-term effects of artificial intelligence on global employment patterns?"
    steps, total_time = await generate_response(prompt)
    for step_title, step_content, step_time in steps:
        print(f"{step_title} (Time: {step_time:.2f}s)")
    print(f"Total thinking time: {total_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())