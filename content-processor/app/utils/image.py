import io
import os
from typing import Dict, Optional

import google.generativeai as genai
import google.generativeai.types as typ
import pytesseract
from PIL import Image


class ImageDescriptionGenerator:
    def __init__(self, api_key: str = None):
        """Initialize with Google Gemini API key."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32,
                "max_output_tokens": 4096,
            },
            tools=[self.get_description_function]
        )

    def generate_description(
        self,
        image_bytes: bytes,
        title: Optional[str] = None,
        user_description: Optional[str] = None
    ) -> Dict:
        """
        Generate a comprehensive description of the image.

        Args:
            image_bytes: Raw image data
            title: Optional image title
            user_description: Optional user-provided description

        Returns:
            Dictionary containing the structured description and metadata
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Extract text from image
            extracted_text = pytesseract.image_to_string(image)

            # Generate description using function calling
            prompt = self._build_description_prompt(
                title, user_description, extracted_text)
            response = self.model.generate_content(
                [prompt, image],
            )

            # Extract structured data from function call
            function_call = response.candidates[0].content.parts[0].function_call
            structured_description = dict(function_call.args)

            # Create vectorizable description
            vectorizable = self._create_vectorizable_description(
                extracted_text,
                structured_description
            )

            return {
                "success": True,
                "extracted_text": extracted_text,
                "structured_description": structured_description,
                "vectorizable_description": vectorizable
            }

        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_description_prompt(
        self,
        title: Optional[str],
        user_description: Optional[str],
        extracted_text: str
    ) -> str:
        """Build a detailed prompt for the description generation."""
        prompt = """
        Provide a comprehensive description of this image using the following structure:

        [CONTENT_SUMMARY]
        - Provide a clear, detailed summary of the main content
        - Include key elements, subjects, and their relationships
        - Describe the overall purpose and context

        [VISUAL_DETAILS]
        - Describe colors, styling, and visual organization
        - Note any significant design elements or patterns
        - Include layout and formatting details

        [TEXT_CONTENT]
        - List and describe every text content present.
        - Include each and every text content present in the image including numbers and characters
        - Include numbers, data, or statistics
        - Note text styling and organization

        [CONTEXT_AND_PURPOSE]
        - Explain the likely purpose or use case
        - Identify target audience
        - Note domain or industry context

        [KEY_TERMS]
        - List 10-15 specific terms that best describe the image
        - Include technical terms if relevant
        - Note any branded or specialized terminology

        Additional Information:
        """

        if title:
            prompt += f"\nTitle: {title}"
        if user_description:
            prompt += f"\nUser Description: {user_description}"
        if extracted_text.strip():
            prompt += f"\nExtracted Text:\n{extracted_text}"

        prompt += """
        
        Guidelines:
        - Be specific and detailed
        - Use clear, descriptive language
        - Include all visible information
        - Maintain factual accuracy
        - Note any uncertainty
        """

        return prompt

    def _create_vectorizable_description(
        self,
        extracted_text: str,
        structured_description: Dict
    ) -> str:
        """Create a single description string optimized for vector search."""
        components = [
            # Start with extracted text
            f"Text Content: {extracted_text}" if extracted_text.strip(
            ) else "",

            # Add main content summary
            "Content Summary: " + \
            " ".join(structured_description['content_summary']),

            # Add key terms for better searchability
            "Key Terms: " + " ".join(structured_description['key_terms']),

            # Add context and purpose
            "Context: " + \
            " ".join(structured_description['context_and_purpose']),

            # Add text content details
            "Text Details: " + " ".join(structured_description['text_content'])
        ]

        return "\n".join([c for c in components if c.strip()])

    @property
    def get_description_function(self) -> genai.types.Tool:
        return genai.types.Tool(
            function_declarations=[{
                "name": "ImageDescription",
                "description": "Provides a structured description of an image.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content_summary": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Clear, detailed summary of the main content."
                        },
                        "visual_details": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Description of colors, styling, and visual organization."
                        },
                        "text_content": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List and description of any text content present."
                        },
                        "context_and_purpose": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Explanation of the likely purpose or use case."
                        },
                        "key_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of 10-15 specific terms that best describe the image."
                        }
                    },
                    "required": [
                        "content_summary",
                        "visual_details",
                        "text_content",
                        "context_and_purpose",
                        "key_terms"
                    ]
                }
            }]
        )
