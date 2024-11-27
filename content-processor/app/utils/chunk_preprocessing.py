import concurrent.futures
import json
import os
from functools import lru_cache
from typing import List, Tuple

from anthropic import Anthropic
from dotenv import load_dotenv

if os.path.exists('.env'):
    load_dotenv()
MAX_CHUNK_SIZE = 20
CONTEXT_WINDOW_SIZE = 40

# print("API key" + os.getenv("ANTHROPIC_API_KEY"))
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

DOCUMENT_CONTEXT_PROMPT = """
<document>
{doc_content}
</document>
"""

CHUNK_CONTEXT_PROMPT = """
Here is the chunk we want to situate within the whole document
<chunk>
{chunk_content}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Answer only with the succinct context and nothing else.
"""


# @lru_cache(maxsize=1024)
def get_context_summary(chunks: Tuple[str, ...], chunk_index: int, client: Anthropic) -> str:
    """
    Get a summary of the context for the given chunk using the Claude 3.5 Haiku LLM.
    This function is cached to improve performance.
    """
    try:
        start = max(0, chunk_index - CONTEXT_WINDOW_SIZE)
        end = min(len(chunks), chunk_index + CONTEXT_WINDOW_SIZE + 1)
        context_chunks = chunks[start:end]
        context_text = "\n\n".join(context_chunks)
        response = client.beta.prompt_caching.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": DOCUMENT_CONTEXT_PROMPT.format(doc_content=context_text),
                            "cache_control": {"type": "ephemeral"}
                        },
                        {
                            "type": "text",
                            "text": CHUNK_CONTEXT_PROMPT.format(chunk_content=chunks[chunk_index])
                        }
                    ]
                }
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error occurred while getting context summary: {e}")
        return ""


def update_chunks(chunks: List[str]) -> List[str]:
    """
    Update the chunks with their corresponding context summaries.
    """
    updated_chunks = []
    # try:
    #     with concurrent.futures.ThreadPoolExecutor() as executor:
    #         futures = []
    #         for i in range(len(chunks)):
    #             futures.append(executor.submit(
    #                 get_context_summary, tuple(chunks), i, client))
    #         for i, future in enumerate(futures):
    #             context_summary = future.result()
    #             updated_chunks.append(f"{context_summary}.{chunks[i]}")
    # except Exception as e:
    #     print(f"Error occurred while updating chunks: {e}")
    # finally:
    #     return updated_chunks
    for i in range(len(chunks)):
        context_summary = get_context_summary(tuple(chunks), i, client)
        updated_chunks.append(f"{context_summary}.{chunks[i]}")
    return updated_chunks


# def get_summary(chunks: List[str]) -> str:
#     """
#     Get a summary of the context for the given chunks using the Claude 3.5 Haiku LLM.
#     This function is cached to improve performance.
#     Returns a list of summaries for each chunk that successfully received a context.
#     """

#     try:
#         response = client.messages.create(
#             model="claude-3-haiku-20240307",
#             max_tokens=1024,
#             temperature=0.0,
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "text",
#                             "text": bulk_summary_prompt.format(
#                                 CHUNK_ARRAY=",\n".join(chunks)),
#                         }
#                     ]
#                 }
#             ],
#             # extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
#         )

#         llm_response = response.content[0].text.strip()
#         return llm_response

#     except Exception as e:
#         print(
#             f"Error occurred while getting context summary': {e}")


# def update_chunks(chunks: List[str]) -> List[str]:
#     """
#     Update the chunks with their corresponding context summaries.
#     """
#     updated_chunks = []
#     PREVIOUS = 10
#     CURRENT = 20
#     NEXT = 10

#     try:
#         for i in range(0, len(chunks), CURRENT):
#             current_context = chunks[i: i + CURRENT]
#             prev_context = chunks[max(0, i - PREVIOUS): i]
#             next_context = chunks[i +
#                                   CURRENT: min(len(chunks), i + CURRENT + NEXT)]
#             context = " ".join(prev_context + current_context + next_context)

#             # Get summary for current chunks
#             context_summary = get_summary(context)

#             # Append context summary to each chunk
#             for chunk in current_context:
#                 updated_chunks.append(f"{context_summary}. {chunk}")

#     except Exception as e:
#         print(f"Error occurred while updating chunks: {e}")

#     return updated_chunks


bulk_summary_prompt = """
You are tasked with creating a summary for an array of text chunks. This summary should serve as a context for each individual chunk in the array, facilitating context-aware chunking for a retrieval-augmented generation (RAG) system.

Here is the array of text chunks:
<chunk_array>
{CHUNK_ARRAY}
</chunk_array>

Your goal is to create a concise summary that captures the essential information and common themes across all chunks. This summary should provide enough context to understand the general topic and key points of the entire text, while being applicable to each individual chunk.

Follow these steps:

1. Carefully read and analyze all the chunks in the array.
2. Identify common themes, key concepts, and important information that appear across multiple chunks.
3. Note any significant proper nouns, dates, or specific details that are crucial to understanding the overall context.
4. Create a summary that incorporates these common elements and provides a high-level overview of the entire text.
5. Ensure that the summary is general enough to be relevant to each individual chunk, but specific enough to provide meaningful context.

Your summary should be concise (aim for 4-5 sentences) yet comprehensive enough to serve as a useful context for any of the individual chunks.

Directly start with the summary without any additional introduction or tags.

Remember, the goal is to create a summary that can act as a useful context for each chunk in the array, enhancing the performance of a RAG system.
"""
