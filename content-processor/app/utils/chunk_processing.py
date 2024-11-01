import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
MAX_CHUNK_SIZE = 20
CONTEXT_WINDOW_SIZE = 40

client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_retries=3
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
    try:
        # Validate input
        # if len(sentences) != 10:
        #     raise ValueError(f"Expected 10 sentences, got {len(sentences)}")

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
                            "text": "<examples>\n<example>\n<CONTEXT>\nClimate change is a complex global phenomenon characterized by long-term shifts in temperature and weather patterns. Primarily driven by human activities, particularly the burning of fossil fuels, it has far-reaching consequences for the planet's ecosystems and human societies. The main driver of climate change is the greenhouse effect, where gases like carbon dioxide trap heat in the Earth's atmosphere, leading to global warming. This warming trend has numerous impacts, including rising sea levels, more frequent and severe weather events, changes in precipitation patterns, and disruptions to ecosystems and biodiversity. The effects of climate change are not uniform across the globe, with some regions experiencing more dramatic changes than others. Climate scientists use various methods to study these changes, including analyzing historical climate data, using computer models to project future scenarios, and observing current environmental indicators. Addressing climate change requires a multifaceted approach, involving mitigation strategies to reduce greenhouse gas emissions and adaptation measures to cope with the changes already underway. International cooperation, technological innovation, and changes in individual and societal behaviors are all crucial components in the global response to this challenge. As the impacts of climate change become more apparent, there is an increasing urgency to implement effective solutions and build resilience in vulnerable communities and ecosystems.\n</CONTEXT>\n<sentence1>\nThe Intergovernmental Panel on Climate Change (IPCC) was established in 1988 to provide policymakers with regular scientific assessments on climate change, its implications, and potential future risks.\n</sentence1>\n<sentence2>\nGreenhouse gases, such as carbon dioxide, methane, and water vapor, play a crucial role in trapping heat within the Earth's atmosphere, contributing to the greenhouse effect.\n</sentence2>\n<sentence3>\nRising global temperatures have led to the melting of polar ice caps and glaciers, contributing to sea level rise and threatening coastal communities worldwide.\n</sentence3>\n<sentence4>\nClimate models predict that some regions may experience increased precipitation, while others may face more frequent and severe droughts as a result of changing weather patterns.\n</sentence4>\n<sentence5>\nThe Paris Agreement, adopted in 2015, aims to limit global temperature increase to well below 2 degrees Celsius above pre-industrial levels, with efforts to limit the increase to 1.5 degrees Celsius.\n</sentence5>\n<sentence6>\nRenewable energy sources, such as solar and wind power, are becoming increasingly important in efforts to reduce greenhouse gas emissions and mitigate climate change.\n</sentence6>\n<sentence7>\nClimate change is affecting biodiversity, with many species struggling to adapt to rapidly changing habitats and facing increased risk of extinction.\n</sentence7>\n<sentence8>\nExtreme weather events, including hurricanes, heatwaves, and wildfires, are becoming more frequent and intense due to climate change, posing significant risks to human health and safety.\n</sentence8>\n<sentence9>\nCarbon pricing mechanisms, such as carbon taxes and cap-and-trade systems, are economic tools designed to incentivize the reduction of greenhouse gas emissions.\n</sentence9>\n<sentence10>\nClimate change adaptation strategies include developing drought-resistant crops, improving flood defenses, and implementing early warning systems for extreme weather events.\n</sentence10>\n<ideal_output>\n{\n    \"sentence1\": \"Description of a key international scientific organization monitoring climate change. Establishes the institutional framework for global climate science and policy interface, setting the foundation for understanding and addressing climate change impacts.\",\n    \n    \"sentence2\": \"Fundamental explanation of the primary mechanism driving climate change. Details the physical process underlying global warming through atmospheric heat retention by specific gases.\",\n    \n    \"sentence3\": \"Direct observable impact of global warming on Earth's cryosphere and coastal regions. Demonstrates the concrete consequences of temperature increases on sea level rise and human communities.\",\n    \n    \"sentence4\": \"Analysis of regional climate change impacts on precipitation patterns. Highlights the uneven distribution of climate change effects and their implications for water availability across different areas.\",\n    \n    \"sentence5\": \"Key international policy response to climate change threats. Outlines specific global temperature targets agreed upon by the international community to prevent dangerous levels of warming.\",\n    \n    \"sentence6\": \"Solution-focused discussion of alternative energy sources for climate change mitigation. Emphasizes technological approaches to reducing greenhouse gas emissions through clean energy adoption.\",\n    \n    \"sentence7\": \"Environmental impact of climate change on species and ecosystems. Illustrates the biological consequences of rapid environmental changes and their effects on global biodiversity.\",\n    \n    \"sentence8\": \"Description of increasing severe weather events linked to climate change. Details the direct threats to human safety and well-being from climate-related weather phenomena.\",\n    \n    \"sentence9\": \"Economic policy tools for addressing climate change through market mechanisms. Explains approaches to incentivize emissions reduction through financial instruments.\",\n    \n    \"sentence10\": \"Practical adaptation strategies for managing climate change impacts. Outlines specific measures being implemented to build resilience against various climate-related challenges.\"\n}\n</ideal_output>\n</example>\n</examples>\n\n",
                            "cache_control": {"type": "ephemeral"}
                        },
                        {
                            "type": "text",
                            "text": prompt,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ],
                },
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        res = response.content[0].text.strip()
        # remove all \n
        res = res.replace("\n", "")

        print("Response")
        print(res)

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

        for i in range(0, len(chunks), CURRENT):
            start = max(0, i - PREVIOUS)
            end = min(len(chunks), i + CURRENT + NEXT)
            context_chunks = chunks[start:end]
            context_text = ",\n".join(context_chunks)
            sentences = chunks[i:i+CURRENT]
            output = get_context_summary_from_anthropic(
                context_text, sentences)

            print("Received")
            output = output.model_dump()
            print(output)

            for j in range(len(sentences)):
                desc = output[f"sentence{j+1}"]
                updated_chunks.append(f"{desc}. {sentences[j]}")

            wait_for_n_seconds(1)
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
