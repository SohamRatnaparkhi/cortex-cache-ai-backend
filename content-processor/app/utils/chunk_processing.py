import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from app.utils.app_logger_config import logger

load_dotenv()
MAX_CHUNK_SIZE = 20
CONTEXT_WINDOW_SIZE = 40

anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_retries=3
)

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    max_retries=3,
)

BULK_CONTEXT_PROMPT = """
You are tasked with generating context-aware descriptions for text chunks to support contextual embeddings in a Retrieval-Augmented Generation (RAG) system. These descriptions will help improve search retrieval by situating each chunk within the overall document.

You will be given the following inputs:

1. Overall Document Context: A brief description that encapsulates the theme or subject of the document.
<context>
{CONTEXT}
</context>

2. Chunked Text: A set of text snippets extracted from the document.
<sentences>
{sentences_xml}
</sentences>

For each chunk, your responsibilities are as follows:

1. Contextual Analysis: Examine the chunk's relevance within the overall document context.
2. Description Creation: Write a short, precise description of how the chunk relates to the document's main theme. Include important contextual elements such as section headings or key points, product names, etc. if applicable.
3. Search Relevance: Ensure the description will enhance the retrievability of this chunk for a search query.
4. Restrict description to 3 to 4 sentences

Improving Retrievability: Your descriptions should help the chunk surface during a search by:
1. Keyword Enrichment: Include key terms or phrases that are likely to match user queries but are also contextually relevant to the chunk.
2. Contextual Precision: Be specific about the chunk's subject matter, avoiding vague terms. This allows embeddings to capture distinct semantic meaning for more accurate search results.
3. Relational Clues: If the chunk provides supporting information (like examples, definitions, or conclusions), ensure the description reflects this to aid in related query retrieval.

Your output should be structured in JSON format, with each string as a key and its context-aware description as the value. Do not use any XML tags in your output.

Here's an example of how your output should be structured:

<ideal_output>
{IDEAL_OUTPUT}
</ideal_output>

Remember, the goal is to create descriptions that will help in building context-aware embeddings. These embeddings should improve the ability to retrieve relevant chunks of text during searches. Your descriptions should reflect the relationship between each chunk and the overall document or topic.

Provide your output in JSON format without any additional commentary or XML tags.
"""
EXAMPLE = """
<examples>
<example>
<CONTEXT>
Climate change refers to long-term shifts in temperature and weather, mainly caused by human activities like burning fossil fuels. It has wide-ranging effects on ecosystems and societies due to the greenhouse effect.
</CONTEXT>
<sentence1>
The IPCC was founded in 1988.
</sentence1>
<sentence2>
Greenhouse gases, such as carbon dioxide and methane, trap heat in the atmosphere.
</sentence2>
<sentence3>
Rising temperatures are melting polar ice and glaciers.
</sentence3>
<sentence4>
Some areas may see more rain, while others face droughts.
</sentence4>
<sentence5>
The Paris Agreement aims to limit global warming to 1.5°C-2°C above pre-industrial levels.
</sentence5>
<sentence6>
Renewable energy, like solar and wind, helps reduce emissions.
</sentence6>
<sentence7>
Many species are struggling to adapt to rapid environmental changes.
</sentence7>
<sentence8>
Extreme weather events are becoming more severe due to climate change.
</sentence8>
<sentence9>
Carbon pricing, such as taxes and cap-and-trade, incentivizes emission reductions.
</sentence9>
<sentence10>
Adaptation strategies include drought-resistant crops and flood defenses.
</sentence10>
<ideal_output>
{
    "sentence1": "Establishes global climate science and policy organization.",
    "sentence2": "Explains the greenhouse effect's role in climate change.",
    "sentence3": "Describes impacts of rising temperatures on polar regions.",
    "sentence4": "Highlights uneven regional impacts of climate change.",
    "sentence5": "Outlines global temperature targets in the Paris Agreement.",
    "sentence6": "Focuses on clean energy solutions for reducing emissions.",
    "sentence7": "Explains biodiversity loss due to rapid environmental changes.",
    "sentence8": "Details increasing extreme weather linked to climate change.",
    "sentence9": "Describes economic tools to reduce greenhouse gas emissions.",
    "sentence10": "Explains practical adaptation strategies for climate resilience."
}
</ideal_output>
</example>
</examples>
"""


class OutputModelStructure(BaseModel):
    sentence1: Optional[str] = ""
    sentence2: Optional[str] = ""
    sentence3: Optional[str] = ""
    sentence4: Optional[str] = ""
    sentence5: Optional[str] = ""
    sentence6: Optional[str] = ""
    sentence7: Optional[str] = ""
    sentence8: Optional[str] = ""
    sentence9: Optional[str] = ""
    sentence10: Optional[str] = ""


def get_context_summary_from_openai(context: str, sentences: List[str]) -> OutputModelStructure:
    res = None
    try:
        sentences_xml = "\n".join([
            f"    <sentence{i+1}> {sentence} </sentence{i+1}>"
            for i, sentence in enumerate(sentences)
        ])

        ideal_output = ""

        for i in range(len(sentences)):
            ideal_output += f"\"sentence{i+1}\": \"Description of the sentence {i+1}.\",\n"

        ideal_output = "{\n" + ideal_output + "\n}"

        # Create the prompt
        prompt = BULK_CONTEXT_PROMPT.format(
            CONTEXT=context, sentences_xml=sentences_xml, IDEAL_OUTPUT=ideal_output)

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "user", "content": EXAMPLE},
                {"role": "user", "content": prompt},
            ],
        )

        logger.debug(response.usage)
        res = response.choices[0].message.content.strip()
        res = res.replace("\n", "")

        logger.debug("Response")
        logger.debug(res)

        # convert to json object
        res = json.loads(res)

        return OutputModelStructure.model_validate(res, strict=False)

        # return res if res != None else manual_parsing(len(sentences), res)
    except Exception as e:
        print(f"Error occurred while getting context summary from openai: {e}")
        return manual_parsing(len(sentences), res)


def get_context_summary_from_anthropic(context: str, sentences: List[str]) -> OutputModelStructure:
    """
    Generate context-aware descriptions for a set of sentences using Anthropic's API.

    Args:
        context (str): The overall document or topic context
        sentences (List[str]): List of 10 sentences to analyze

    Returns:
        OutputModelStructure: Pydantic model containing context-aware descriptions

    Raises:
        ValueError: If not exactly 10 sentences are provided
    """
    res = None
    try:
        # Create the sentences XML block
        sentences_xml = "\n".join([
            f"    <sentence{i+1}> {sentence} </sentence{i+1}>"
            for i, sentence in enumerate(sentences)
        ])

        ideal_output = ""

        for i in range(len(sentences)):
            ideal_output += f"\"sentence{i+1}\": \"Description of the sentence {i+1}.\",\n"

        ideal_output = "{\n" + ideal_output + "\n}"

        # Create the prompt
        prompt = BULK_CONTEXT_PROMPT.format(
            CONTEXT=context, sentences_xml=sentences_xml, IDEAL_OUTPUT=ideal_output)

        response = anthropic_client.beta.prompt_caching.messages.create(
            model="claude-3-haiku-20240307",
            temperature=0.0,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": EXAMPLE,
                            "cache_control": {"type": "ephemeral"}
                        },
                        {
                            "type": "text",
                            "text": prompt,
                            # "cache_control": {"type": "ephemeral"}
                        }
                    ],
                },
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        logger.debug(response.usage)
        res = response.content[0].text.strip()
        # remove all \n
        res = res.replace("\n", "")

        logger.debug("Response")
        logger.debug(res)

        # convert to json object
        res = json.loads(res)

        return OutputModelStructure.model_validate(res, strict=False)
    except Exception as e:
        print(f"Error occurred while getting context summary: {e}")
        return manual_parsing(len(sentences), res)


def wait_for_n_seconds(n: int = 5) -> None:
    time.sleep(n)
    return None


def update_chunks(chunks: List[str]) -> List[str]:
    try:
        updated_chunks = []

        PREVIOUS = 30
        NEXT = 30
        CURRENT = 10

        # Split the chunks into batches for anthropic and openai
        anthropic_batches = []
        openai_batches = []

        for i in range(0, len(chunks), CURRENT):
            start = max(0, i - PREVIOUS)
            end = min(len(chunks), i + CURRENT + NEXT)
            batch = {
                'start': start,
                'end': end,
                'current_start': i,
                'current_end': i + CURRENT
            }
            if (i // CURRENT) % 2 == 0:
                anthropic_batches.append(batch)
            else:
                openai_batches.append(batch)

        def process_batches(batches, model):
            for batch in batches:
                context_chunks = chunks[batch['start']:batch['end']]
                context_text = ",\n".join(context_chunks)
                sentences = chunks[batch['current_start']:batch['current_end']]

                if model == 'openai':
                    output = get_context_summary_from_openai(
                        context_text, sentences)
                elif model == 'anthropic':
                    output = get_context_summary_from_anthropic(
                        context_text, sentences)
                else:
                    raise ValueError("Unknown model")

                output = output.model_dump()

                for j in range(len(sentences)):
                    desc = output[f"sentence{j+1}"]
                    updated_chunks.append(f"{desc}. {sentences[j]}")

                wait_for_n_seconds(5)

        # Create threads for anthropic and openai batches
        thread1 = threading.Thread(
            target=process_batches, args=(anthropic_batches, 'anthropic'))
        thread2 = threading.Thread(
            target=process_batches, args=(openai_batches, 'openai'))

        # Start the threads
        thread1.start()
        thread2.start()

        # Wait for both threads to finish
        thread1.join()
        thread2.join()

        print("Updated chunks length - " + str(len(updated_chunks)))
        return updated_chunks
    except Exception as e:
        print(f"Error occurred while updating chunks: {e}")
        return []


@dataclass
class ParsingResult:
    value: str
    success: bool
    error: Optional[str] = None


class ResponseParser:
    @staticmethod
    def clean_response(response: str) -> str:
        """Clean and normalize the response string."""
        if not response:
            return ""
        # Remove newlines and extra whitespace
        cleaned = re.sub(r'\s+', ' ', response.strip())
        # Remove any potential markdown code block markers
        cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', cleaned)
        return cleaned

    @staticmethod
    def extract_json_like_string(response: str) -> str:
        """Extract content between outermost curly braces."""
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
        return match.group(0) if match else response

    @staticmethod
    def parse_single_key(response: str, current_key: str) -> ParsingResult:
        """
        Parse a single key from the response string with improved error handling.

        Args:
            response: The full response string
            current_key: The key to parse for (e.g., "sentence1")

        Returns:
            ParsingResult containing the parsed value and status information
        """
        try:
            # Look for the key pattern with various quote styles
            key_patterns = [
                f'"{current_key}"\\s*:',
                f"'{current_key}'\\s*:",
                f"{current_key}\\s*:"
            ]

            # Find the start of the current key's value
            start_index = -1
            for pattern in key_patterns:
                match = re.search(pattern, response)
                if match:
                    start_index = match.end()
                    break

            if start_index == -1:
                return ParsingResult("", False, f"Key {current_key} not found")

            # Extract the value until the next key or end of object
            value_pattern = r'\s*"([^"\\]*(?:\\.[^"\\]*)*)"|\s*\'([^\'\\]*(?:\\.[^\'\\]*)*)\'|\s*([^,}\s][^,}]*)'
            match = re.match(value_pattern, response[start_index:])

            if not match:
                return ParsingResult("", False, f"No valid value found for {current_key}")

            # Get the matched value from whichever group succeeded
            value = next((g for g in match.groups() if g is not None), "")

            # Clean up the value
            value = value.strip().strip('"\'').strip()

            return ParsingResult(value, True)

        except Exception as e:
            return ParsingResult("", False, f"Error parsing {current_key}: {str(e)}")

    @staticmethod
    def parse_response(response: str, expected_sentences: int) -> Dict[str, str]:
        """
        Parse the entire response with fallback strategies.

        Args:
            response: The response string to parse
            expected_sentences: Number of sentences to extract

        Returns:
            Dictionary mapping sentence keys to their values
        """
        result = {}

        # Clean the response first
        cleaned_response = ResponseParser.clean_response(response)

        # Try parsing as JSON first
        try:
            result = json.loads(cleaned_response)
            return result
        except json.JSONDecodeError:
            pass

        # Extract content between curly braces if present
        cleaned_response = ResponseParser.extract_json_like_string(
            cleaned_response)

        # Fallback to manual parsing
        for i in range(expected_sentences):
            current_key = f"sentence{i+1}"
            parsing_result = ResponseParser.parse_single_key(
                cleaned_response, current_key)

            if parsing_result.success:
                result[current_key] = parsing_result.value
            else:
                result[current_key] = ""  # Set empty string for failed parses

        return result


def manual_parsing(sentences_length: int, response: str) -> OutputModelStructure:
    """
    Improved manual parsing function with better error handling and robustness.

    Args:
        sentences_length: Number of sentences to parse
        response: The response string to parse

    Returns:
        OutputModelStructure with parsed values
    """
    output = OutputModelStructure()

    try:
        # Parse the response
        parsed_dict = ResponseParser.parse_response(response, sentences_length)

        # Set attributes on the output model
        for i in range(sentences_length):
            current_key = f"sentence{i+1}"
            value = parsed_dict.get(current_key, "")
            setattr(output, current_key, value)

    except Exception as e:
        print(f"Error occurred during improved manual parsing: {e}")

    return output
