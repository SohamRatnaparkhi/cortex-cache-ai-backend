import re
from dataclasses import dataclass
from functools import lru_cache
from logging import getLogger
from typing import Dict, List, Optional, Tuple, TypedDict

from app.schemas.web_agent import ReRankedWebSearchResult

logger = getLogger(__name__)


@dataclass(frozen=True)
class ContentLimits:
    """Immutable content length limits"""
    MAX_RESULTS: int = 5
    MAX_TITLE_LENGTH: int = 100
    MAX_CONTENT_LENGTH: int = 1000
    MAX_TOTAL_LENGTH: int = 4000
    MIN_SENTENCE_SCORE: float = 0.3


@dataclass
class ContentStats:
    total_chars: int = 0
    results_included: int = 0
    total_score: float = 0.0

    def can_add_content(self, length: int, limits: ContentLimits) -> bool:
        return (self.total_chars + length <= limits.MAX_TOTAL_LENGTH and
                self.results_included < limits.MAX_RESULTS)


@lru_cache(maxsize=1000)
def clean_text(text: str) -> str:
    """Cache cleaned text operations"""
    if not text:
        return ""
    text = re.sub(r'[^\x20-\x7E]|\s+', ' ', text.strip())
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class WebDataFormatter:
    def __init__(self, limits: ContentLimits = ContentLimits()):
        self.limits = limits
        self.stats = ContentStats()

    def format_additional_info(self, info: Dict[str, any]) -> str:
        """Format additional info without caching"""
        if not info:
            return ""

        info_items = []
        for key, value in sorted(info.items()):
            if value:
                clean_value = clean_text(str(value))[:50]
                info_items.append(f'        <{key}>{clean_value}</{key}>')

        if not info_items:
            return ""

        return "\n".join([
            "    <additional_info>",
            "\n".join(info_items),
            "    </additional_info>"
        ])

    def estimate_result_size(self, result: ReRankedWebSearchResult, content_length: int) -> int:
        """Estimate the size of a formatted result without actually formatting it"""
        title_len = min(len(result['title']), self.limits.MAX_TITLE_LENGTH)
        url_len = min(len(result['url']), self.limits.MAX_TITLE_LENGTH)
        source_len = min(len(str(result.get('source', 'web'))), 20)

        # Basic XML structure size
        base_size = len("<web_data>\n    <title></title>\n    <url></url>\n    "
                        "<content></content>\n    <source></source>\n    "
                        "<score></score>\n</web_data>")

        # 20 for score and padding
        return base_size + title_len + url_len + content_length + source_len + 20

    def smart_truncate_content(self, content: str, result_score: float, available_space: int) -> str:
        """Truncate content using result score and available space"""
        if not content:
            return ""

        max_length = min(self.limits.MAX_CONTENT_LENGTH, available_space)

        if len(content) <= max_length:
            return clean_text(content)

        sentences = content.split('. ')

        # Always include first sentence if possible
        first_sentence = clean_text(sentences[0])
        if len(first_sentence) > max_length:
            return first_sentence[:max_length-3] + "..."

        selected_sentences = [first_sentence]
        current_length = len(first_sentence)

        # Score and sort remaining sentences
        scored_sentences = []
        for idx, sentence in enumerate(sentences[1:], 1):
            clean_sentence = clean_text(sentence)
            length = len(clean_sentence)

            if length < 10 or length > 200:
                continue

            position_score = 0.8 if idx == len(sentences) - 1 else 0.6
            content_score = sum([
                0.2 * any(c.isdigit() for c in clean_sentence),
                0.3 * any(word in clean_sentence.lower()
                          for word in ['important', 'key', 'main', 'significant', 'crucial']),
                0.5 * (20 <= length <= 150)
            ])

            final_score = (position_score + content_score) * result_score
            if final_score >= self.limits.MIN_SENTENCE_SCORE:
                scored_sentences.append((clean_sentence, final_score, length))

        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        # Add sentences while respecting space constraints
        for sentence, _, length in scored_sentences:
            if current_length + length + 2 <= max_length:
                selected_sentences.append(sentence)
                current_length += length + 2
            else:
                break

        return '. '.join(selected_sentences) + ('...' if len(sentences) > len(selected_sentences) else '')

    def format_result(self, result: ReRankedWebSearchResult, available_space: int) -> Tuple[str, int]:
        """Format a single search result with space constraints"""
        title = clean_text(result['title'])[:self.limits.MAX_TITLE_LENGTH]
        url = clean_text(result['url'])[:self.limits.MAX_TITLE_LENGTH]
        source = clean_text(result.get('source', 'web'))[:20]
        score = result.get('score', 0.0)

        # Calculate space needed for basic structure
        # 200 for XML tags and padding
        base_structure_size = len(title) + len(url) + len(source) + 200
        content_space = min(
            available_space - base_structure_size, self.limits.MAX_CONTENT_LENGTH)

        if content_space <= 0:
            content = ""
        else:
            content = self.smart_truncate_content(
                result.get('content', ''), score, content_space)

        info_str = self.format_additional_info(
            result.get('additional_info', {}))

        entry_parts = [
            "<web_data>",
            f"    <title>{title}</title>",
            f"    <url>{url}</url>",
            f"    <content>{content}</content>",
            f"    <source>{source}</source>",
            f"    <score>{score:.3f}</score>"
        ]

        if info_str:
            entry_parts.append(info_str)

        entry_parts.append("</web_data>")
        entry = "\n".join(entry_parts)

        return entry, len(entry)

    def format_web_data(self, query: str, results: List[ReRankedWebSearchResult]) -> Tuple[str, ContentStats]:
        """Format all web data with optimized space allocation"""
        try:
            clean_query = clean_text(query)[:self.limits.MAX_TITLE_LENGTH]
            query_wrapper_size = len(
                "<web_search>\n<question></question>\n</web_search>")
            total_available_space = self.limits.MAX_TOTAL_LENGTH - \
                query_wrapper_size - len(clean_query)

            self.stats = ContentStats()
            data_entries = []

            # Sort results by score
            sorted_results = sorted(
                results,
                key=lambda x: x.get('score', 0),
                reverse=True
            )[:self.limits.MAX_RESULTS]

            # First pass: calculate minimum sizes and allocate space
            total_min_size = 0
            result_sizes = []

            for result in sorted_results:
                min_size = self.estimate_result_size(
                    result, 50)  # Minimum content size
                result_sizes.append(min_size)
                total_min_size += min_size

            if total_min_size <= total_available_space:
                # We can include all results, distribute remaining space
                extra_space = (total_available_space -
                               total_min_size) // len(sorted_results)

                for idx, result in enumerate(sorted_results):
                    space_for_result = result_sizes[idx] + extra_space
                    entry, entry_size = self.format_result(
                        result, space_for_result)

                    data_entries.append(entry)
                    self.stats.total_chars += entry_size
                    self.stats.results_included += 1
                    self.stats.total_score += result.get('score', 0.0)
            else:
                # Can't fit all results, maximize what we can include
                remaining_space = total_available_space
                for result in sorted_results:
                    entry, entry_size = self.format_result(
                        result, remaining_space)

                    if entry_size <= remaining_space:
                        data_entries.append(entry)
                        remaining_space -= entry_size
                        self.stats.total_chars += entry_size
                        self.stats.results_included += 1
                        self.stats.total_score += result.get('score', 0.0)
                    else:
                        break

            formatted_data = (
                f"<web_search>\n<question>{clean_query}</question>\n" +
                "\n".join(data_entries) +
                "\n</web_search>"
            )

            return formatted_data, self.stats

        except Exception as e:
            logger.error(f"Error formatting web data: {str(e)}", exc_info=True)
            error_response = f"<web_search>\n<question>{query}</question>\n<error>Error formatting results</error>\n</web_search>"
            self.stats = ContentStats(total_chars=len(error_response))
            return error_response, self.stats
