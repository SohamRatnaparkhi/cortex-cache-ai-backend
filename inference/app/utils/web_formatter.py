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
    MAX_CONTENT_LENGTH: int = 300
    MAX_TOTAL_LENGTH: int = 1000
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
    # Combine regex operations
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
        for key, value in sorted(info.items()):  # Sort for consistency
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

    def smart_truncate_content(self, content: str, result_score: float) -> str:
        """Truncate content using result score and content analysis"""
        if not content:
            return ""

        if len(content) <= self.limits.MAX_CONTENT_LENGTH:
            return clean_text(content)

        sentences = content.split('. ')

        # Calculate sentence scores
        scored_sentences: List[Tuple[str, float, int]] = []

        for idx, sentence in enumerate(sentences):
            if not sentence:
                continue

            clean_sentence = clean_text(sentence)
            length = len(clean_sentence)

            # Skip very short or very long sentences
            if length < 10 or length > 200:
                continue

            # Position scoring
            position_score = 1.0 if idx == 0 or idx == len(
                sentences) - 1 else 0.8

            # Content scoring
            content_score = sum([
                0.2 * any(c.isdigit() for c in clean_sentence),  # Has numbers
                0.3 * any(word in clean_sentence.lower()
                          for word in ['important', 'key', 'main', 'significant', 'crucial']),  # Key terms
                0.5 * (20 <= length <= 150)  # Ideal length
            ])

            final_score = (position_score + content_score) * result_score

            if final_score >= self.limits.MIN_SENTENCE_SCORE:
                scored_sentences.append((clean_sentence, final_score, length))

        # Sort and select sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        selected_sentences = []
        total_length = 0

        # Always include first sentence if it exists
        if sentences and sentences[0]:
            first_sentence = clean_text(sentences[0])
            if len(first_sentence) <= self.limits.MAX_CONTENT_LENGTH:
                selected_sentences.append(first_sentence)
                total_length = len(first_sentence) + 2

        # Add highest scoring sentences that fit
        for sentence, _, length in scored_sentences:
            if sentence not in selected_sentences:  # Avoid duplicates
                if total_length + length + 2 <= self.limits.MAX_CONTENT_LENGTH:
                    selected_sentences.append(sentence)
                    total_length += length + 2
                else:
                    break

        return '. '.join(selected_sentences) + ('...' if selected_sentences else '')

    def format_result(self, result: ReRankedWebSearchResult) -> Tuple[str, int]:
        """Format a single search result"""
        title = clean_text(result['title'])[:self.limits.MAX_TITLE_LENGTH]
        url = clean_text(result['url'])[:self.limits.MAX_TITLE_LENGTH]
        source = clean_text(result.get('source', 'web'))[:20]
        score = result.get('score', 0.0)

        # Format content
        content = self.smart_truncate_content(result.get('content', ''), score)

        # Format additional info
        info_str = self.format_additional_info(
            result.get('additional_info', {}))

        # Build entry
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
        """Format all web data"""
        try:
            # Sort results by score
            sorted_results = sorted(
                results,
                key=lambda x: x.get('score', 0),
                reverse=True
            )[:self.limits.MAX_RESULTS]

            # Process query
            clean_query = clean_text(query)[:self.limits.MAX_TITLE_LENGTH]
            self.stats = ContentStats(total_chars=len(
                clean_query) + 50)  # Reset stats

            # Process results
            data_entries = []

            for result in sorted_results:
                entry, entry_size = self.format_result(result)

                if not self.stats.can_add_content(entry_size, self.limits):
                    break

                data_entries.append(entry)
                self.stats.total_chars += entry_size
                self.stats.results_included += 1
                self.stats.total_score += result.get('score', 0.0)

            # Build final output
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
