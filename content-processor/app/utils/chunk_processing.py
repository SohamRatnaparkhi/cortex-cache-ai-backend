import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fireworks.client import AsyncFireworks
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.utils.app_logger_config import logger
from app.utils.status_tracking import TRACKER, ProcessingStatus

if os.path.exists('.env'):
    load_dotenv()

MAX_CHUNK_SIZE = 20
CONTEXT_WINDOW_SIZE = 40

fireworks_client = AsyncFireworks(
    api_key=os.getenv("FIREWORKS_API_KEY"),
)

anthropic_client = AsyncAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_retries=3
)

openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    max_retries=3,
)

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_retries=3,
    base_url="https://api.deepseek.com",
)

BULK_CONTEXT_PROMPT = """
You are an expert in contextual analysis and semantic search optimization. Your task is to generate precise, search-optimized descriptions for text chunks that will enhance retrieval in a RAG system.

INPUT:
1. Document Context:
<context>
{CONTEXT}
</context>

2. Text Chunks:
<sentences>
{sentences_xml}
</sentences>

REQUIREMENTS:
1. Generate descriptions that:
   - Capture the semantic relationship with the document context
   - Include key entities, technical terms, and domain-specific vocabulary
   - Maintain hierarchical context (e.g., section/subsection relationships)
   - Are optimized for semantic search retrieval
   - Are exactly 3 sentences long for consistency

2. Each description must include:
   - Primary topic/subject of the chunk
   - Relationship to the document's main theme
   - Supporting details or examples if present
   - Technical terminology preserved verbatim

3. Search Optimization Guidelines:
   - Incorporate likely search terms naturally
   - Use precise, domain-specific language
   - Include relevant synonyms or related concepts
   - Preserve hierarchical information

OUTPUT FORMAT:
- Pure JSON object
- Each key is the sentence identifier
- Each value is the optimized description
- No XML tags or additional commentary

Example structure:
{IDEAL_OUTPUT}

Focus on creating descriptions that will generate embeddings capable of:
1. Accurate semantic matching
2. Context-aware retrieval
3. Hierarchical understanding
4. Technical precision

Respond only with the JSON output, no additional text."""

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


EXAMPLE JSON OUTPUT:
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


async def get_context_from_fireworks(context, sentences: List[str]) -> List[str]:
    """
    Get context for the sentences from the Fireworks API.

    Args:
        context (str): The overall document or topic context
        sentences (List[str]): List of sentences to analyze

    Returns:
        List[str]: List of context descriptions for each sentence
    """
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

        response = await fireworks_client.chat.completions.acreate(
            model="accounts/fireworks/models/deepseek-v3",
            temperature=0.0,
            messages=[
                {"role": "user", "content": EXAMPLE},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        # logger.debug(response.usage)
        # print(response)
        res = response.choices[0].message.content

        # convert to json object
        res = json.loads(res)

        return OutputModelStructure.model_validate(res, strict=False)

    except Exception as e:
        print("Error occurred while getting context from fireworks: ", e)
        return manual_parsing(len(sentences), res)


async def get_context_summary_from_openai(context: str, sentences: List[str], is_deepseek=False) -> OutputModelStructure:
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

        # client = deepseek_client if is_deepseek else openai_client
        # model = "deepseek-chat" if is_deepseek else "gpt-4o-mini"
        response = await openai_client.chat.completions.create(
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
        print(
            f"Error occurred while getting context summary from openai: {e}, res: {res}")
        return manual_parsing(len(sentences), res)


async def get_context_summary_from_anthropic(context: str, sentences: List[str]) -> OutputModelStructure:
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

        response = await anthropic_client.beta.prompt_caching.messages.create(
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
        # if response.
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
        print(
            f"Error occurred while getting context summary: {e}: res = {res}")
        return manual_parsing(len(sentences), res)


def wait_for_n_seconds(n: int = 5) -> None:
    time.sleep(n)
    return None


async def update_chunks(chunks: List[str], userId, memoryId) -> List[str]:
    try:
        updated_chunks = []
        PREVIOUS = 30
        NEXT = 30
        CURRENT = 10

        # Split chunks into batches for three models based on ratios
        deepseek_batches = []
        openai_batches = []
        claude_batches = []

        TRACKER.update_status(
            userId, memoryId, ProcessingStatus.CONTEXTUALIZING, 20)

        total_chunks = len(chunks)
        max_percentage = 80

        step_size_for_percentage_update = 10
        chunks_per_step = max(
            (total_chunks // step_size_for_percentage_update), 1)
        percentage_update_per_step = max_percentage // chunks_per_step if chunks_per_step > 0 else max_percentage

        # Distribute chunks based on ratios (0.5, 0.3, 0.2)
        for i in range(0, len(chunks), CURRENT):
            start = max(0, i - PREVIOUS)
            end = min(len(chunks), i + CURRENT + NEXT)
            batch = {
                'start': start,
                'end': end,
                'current_start': i,
                'current_end': i + CURRENT
            }

            # Use modulo 10 to distribute according to ratios
            # 0-4 (5 numbers) -> Deepseek (50%)
            # 5-7 (3 numbers) -> OpenAI (30%)
            # 8-9 (2 numbers) -> Claude (20%)
            distribution_index = (i // CURRENT) % 10

            if distribution_index < 5:
                deepseek_batches.append(batch)
            elif distribution_index < 8:
                openai_batches.append(batch)
            else:
                claude_batches.append(batch)

        async def process_batches(batches, model):
            percentage = 20
            batch_results = []
            for batch in batches:
                context_chunks = chunks[batch['start']:batch['end']]
                context_text = ",\n".join(context_chunks)
                sentences = chunks[batch['current_start']:batch['current_end']]

                if model == 'openai':
                    output = await get_context_summary_from_openai(context_text, sentences, is_deepseek=False)
                elif model == 'deepseek':
                    output = await get_context_from_fireworks(context_text, sentences)
                elif model == 'claude':
                    output = await get_context_summary_from_anthropic(context_text, sentences)
                else:
                    raise ValueError(f"Unknown model: {model}")

                output = output.model_dump()
                for j in range(len(sentences)):
                    desc = output[f"sentence{j+1}"]
                    batch_results.append(f"{desc}. {sentences[j]}")

                percentage = min(
                    percentage + percentage_update_per_step, max_percentage)
                TRACKER.update_status(
                    userId, memoryId, ProcessingStatus.CONTEXTUALIZING, percentage)
                await asyncio.sleep(5)  # Non-blocking sleep
            return batch_results

        # Create and gather tasks for concurrent execution
        tasks = [
            process_batches(deepseek_batches, 'deepseek'),
            process_batches(openai_batches, 'openai'),
            process_batches(claude_batches, 'claude')
        ]

        # Wait for all tasks to complete and gather results
        results = await asyncio.gather(*tasks)

        # Combine results from all tasks
        for batch_result in results:
            updated_chunks.extend(batch_result)

        print(f"Updated chunks length - {len(updated_chunks)}")
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
