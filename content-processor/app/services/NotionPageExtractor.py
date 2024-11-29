from typing import Any, Dict, List, Optional

import requests


class NotionTextExtractor:
    def __init__(self, page_id: str, access_token: str):
        self.page_id = page_id
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.notion.com/v1"

    def get_block_children(self, block_id: str, start_cursor: Optional[str] = None) -> Dict[str, Any]:
        """Fetch children blocks of a given block."""
        url = f"{self.base_url}/blocks/{block_id}/children"
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_page_properties(self) -> Dict[str, Any]:
        """Fetch page properties for additional context."""
        url = f"{self.base_url}/pages/{self.page_id}"
        response = requests.get(url, headers=self.headers)
        # response.raise_for_status()
        print(response.json())

        response.raise_for_status()
        return response.json()

    def extract_text_from_rich_text(self, rich_text: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array, preserving important formatting."""
        text_parts = []
        for text in rich_text:
            content = text.get("plain_text", "")
            annotations = text.get("annotations", {})

            # Preserve important formatting that might affect meaning
            if annotations.get("code"):
                content = f"`{content}`"
            if annotations.get("bold"):
                content = f"**{content}**"
            if annotations.get("italic"):
                content = f"_{content}_"

            text_parts.append(content)

        return " ".join(text_parts)

    def extract_table_row_content(self, row: List[Dict[str, Any]]) -> List[str]:
        """Extract content from a table row."""
        return [self.extract_text_from_rich_text(cell.get("rich_text", [])) for cell in row]

    def process_block_content(self, block: Dict[str, Any]) -> str:
        """Process a single block and extract its semantic content."""
        block_type = block.get("type", "")
        if not block_type:
            return ""

        block_content = block.get(block_type, {})
        text = ""

        try:
            # Text-based blocks
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3",
                              "heading_4", "heading_5", "heading_6"]:
                text = self.extract_text_from_rich_text(
                    block_content.get("rich_text", []))
                # Add semantic markers for headings
                if block_type.startswith("heading"):
                    level = block_type[-1]
                    text = f"[H{level}] {text}"

            # List items
            elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                text = self.extract_text_from_rich_text(
                    block_content.get("rich_text", []))

            # Structured text
            elif block_type == "quote":
                text = f"Quote: {self.extract_text_from_rich_text(block_content.get('rich_text', []))}"

            elif block_type == "callout":
                emoji = block_content.get("icon", {}).get("emoji", "")
                text = f"Callout {emoji}: {self.extract_text_from_rich_text(block_content.get('rich_text', []))}"

            elif block_type == "toggle":
                text = self.extract_text_from_rich_text(
                    block_content.get("rich_text", []))

            # Code and technical content
            elif block_type == "code":
                language = block_content.get("language", "")
                code_text = self.extract_text_from_rich_text(
                    block_content.get("rich_text", []))
                text = f"Code ({language}): {code_text}"

            elif block_type == "equation":
                text = f"Equation: {block_content.get('expression', '')}"

            # Database and table content
            elif block_type == "table":
                # Placeholder - actual content processed in children
                text = "[Table Content]"

            elif block_type == "column_list":
                text = ""  # Content will be processed in children

            elif block_type == "column":
                text = ""  # Content will be processed in children

            # Interactive elements
            elif block_type == "to_do":
                status = "✓" if block_content.get("checked") else "☐"
                text = f"Task {status}: {self.extract_text_from_rich_text(block_content.get('rich_text', []))}"

            elif block_type == "bookmark":
                url = block_content.get("url", "")
                caption = self.extract_text_from_rich_text(
                    block_content.get("caption", []))
                text = f"Bookmark: {caption} ({url})"

            # Rich content
            elif block_type == "table_of_contents":
                text = "[Table of Contents]"

            elif block_type == "breadcrumb":
                text = "[Navigation Breadcrumb]"

            # Synced blocks
            elif block_type == "synced_block":
                # Content will be processed through children if available
                text = ""

            # Templates
            elif block_type == "template":
                text = self.extract_text_from_rich_text(
                    block_content.get("rich_text", []))

            # Other structural elements
            elif block_type == "divider":
                text = "---"

            elif block_type == "link_preview":
                text = f"Link: {block_content.get('url', '')}"

            # Child databases
            elif block_type == "child_database":
                text = f"Database: {block_content.get('title', '')}"

            # Child pages
            elif block_type == "child_page":
                text = f"Subpage: {block_content.get('title', '')}"

        except Exception as e:
            print(f"Error processing block type {block_type}: {e}")
            return ""

        return text.strip()

    def process_blocks_recursively(self, block_id: str, indent_level: int = 0) -> str:
        """Recursively process blocks and their children, maintaining semantic context."""
        all_text = []
        has_more = True
        start_cursor = None
        current_list_type = None

        while has_more:
            try:
                response = self.get_block_children(block_id, start_cursor)
                blocks = response.get("results", [])

                for block in blocks:
                    block_type = block.get("type", "")
                    block_text = self.process_block_content(block)

                    # Handle list continuity for better semantic chunking
                    if block_type in ["numbered_list_item", "bulleted_list_item"]:
                        if current_list_type != block_type:
                            current_list_type = block_type
                            # Add spacing between different lists
                            all_text.append("")
                    else:
                        current_list_type = None

                    # Add processed text with proper indentation
                    if block_text:
                        indented_text = "  " * indent_level + block_text
                        all_text.append(indented_text)

                    # Process children recursively
                    if block.get("has_children", False):
                        child_text = self.process_blocks_recursively(
                            block["id"],
                            indent_level + 1
                        )
                        if child_text:
                            # For certain block types, we want to keep children closer
                            if block_type in ["toggle", "quote", "callout"]:
                                all_text.append(
                                    "  " * indent_level + child_text)
                            else:
                                all_text.append(child_text)

                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

            except requests.exceptions.RequestException as e:
                print(f"Error fetching blocks: {e}")
                break

        return "\n".join(text for text in all_text if text.strip())

    def get_page_content(self) -> str:
        """
        Main method to process the page and extract all text content,
        optimized for semantic chunking and vector search.
        """
        try:
            # Get page properties for context
            page_properties = self.get_page_properties()

            # Extract page title and create a header
            title = "Untitled"
            if "properties" in page_properties:
                for prop in page_properties["properties"].values():
                    if prop.get("type") == "title":
                        title_text = prop.get("title", [])
                        if title_text:
                            title = self.extract_text_from_rich_text(
                                title_text)
                            break

            # Combine page title with content
            header = f"[Page Title] {title}\n\n"
            content = self.process_blocks_recursively(self.page_id)

            return header + content

        except Exception as e:
            print(f"Error processing page: {e}")
            return ""
