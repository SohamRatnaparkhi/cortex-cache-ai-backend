import re
from typing import Optional

import requests
from bs4 import BeautifulSoup


class ContentFetcher:
    """Helper class to fetch and parse content from different sources"""

    @staticmethod
    def get_headers():
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""

        # Replace multiple newlines with single newline
        text = re.sub(r'\n\s*\n', '\n', text)

        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove very short lines (likely navigation/UI elements)
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if len(line) > 30]

        return '\n'.join(lines)

    @staticmethod
    def fetch_web_content(url: str) -> Optional[str]:
        """Fetch and extract main content from a webpage."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Use lxml parser for better performance
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe',
                                          'noscript', 'aside', 'form', 'button']):
                element.decompose()

            # Initialize content storage
            content_text = []

            # Strategy 1: Look for article schema
            article_schema = soup.find(
                'article', itemtype="http://schema.org/Article")
            if article_schema:
                content_text.append(ContentFetcher.clean_text(
                    article_schema.get_text()))
                return content_text[0]

            # Strategy 2: Look for main article content
            main_article = soup.find(
                ['article', 'main', '[role="main"]', '[role="article"]'])
            if main_article:
                content_text.append(
                    ContentFetcher.clean_text(main_article.get_text()))
                return content_text[0]

            # Strategy 3: Look for content-specific div classes
            content_divs = soup.find_all(['div', 'section'], class_=re.compile(
                r'(content|article|post|entry|text|body)(?!.*(?:sidebar|comment|footer|header|navigation))',
                re.I))
            if content_divs:
                # Get the div with the most text content
                main_div = max(content_divs, key=lambda x: len(
                    x.get_text().strip()))
                content_text.append(
                    ContentFetcher.clean_text(main_div.get_text()))
                return content_text[0]

            # Strategy 4: Collect all meaningful paragraphs
            paragraphs = soup.find_all('p')
            if paragraphs:
                meaningful_paragraphs = [
                    p.get_text() for p in paragraphs
                    if len(p.get_text().strip()) > 50
                    and not re.search(r'copyright|privacy|cookie|terms|subscribe|newsletter',
                                      p.get_text(), re.I)
                    and not any(nav in p.get_text().lower()
                                for nav in ['menu', 'navigation', 'skip to content'])
                ]
                if meaningful_paragraphs:
                    content_text.append(ContentFetcher.clean_text(
                        ' '.join(meaningful_paragraphs)))
                    return content_text[0]

            # Strategy 5: Last resort - get all text from body
            if not content_text:
                body = soup.find('body')
                if body:
                    content_text.append(
                        ContentFetcher.clean_text(body.get_text()))
                    return content_text[0]

            return None

        except Exception as e:
            print(f"Error fetching content from {url}: {str(e)}")
            return None

    @ staticmethod
    def fetch_github_readme(url: str) -> Optional[str]:
        """Fetch GitHub repository README content."""
        try:
            # Convert GitHub URL to raw content URL
            parts = url.strip('/').split('/')
            if len(parts) >= 5:
                owner = parts[3]
                repo = parts[4]

                # Try common README filenames
                readme_files = [
                    'README.md',
                    'README',
                    'README.txt',
                    'readme.md',
                    'Readme.md'
                ]

                for readme_file in readme_files:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{readme_file}"
                    response = requests.get(raw_url, timeout=5)

                    if response.status_code == 200:
                        content = response.text
                        return ContentFetcher.clean_text(content) if content else None

            return None

        except Exception as e:
            print(f"Error fetching GitHub README from {url}: {str(e)}")
            return None

    @ staticmethod
    def fetch_reddit_content(url: str) -> Optional[str]:
        """Fetch Reddit content by converting to JSON API URL."""
        try:
            # Convert regular Reddit URL to JSON API URL
            if not url.endswith('.json'):
                url = url + '.json'

            response = requests.get(
                url,
                headers=ContentFetcher.get_headers(),
                timeout=5
            )
            response.raise_for_status()

            data = response.json()

            content_parts = []

            # Extract content based on Reddit's JSON structure
            if isinstance(data, list) and len(data) > 0:
                post_data = data[0]['data']['children'][0]['data']

                # Add post title and content
                title = post_data.get('title', '')
                if title:
                    content_parts.append(f"Title: {title}")

                selftext = post_data.get('selftext', '')[0: 200]
                if selftext:
                    content_parts.append(f"Post Content: {selftext}")

                # Add top comments if available
                if len(data) > 1:
                    comments = data[1]['data']['children']
                    comment_count = 0
                    for comment in comments:
                        # Regular comment, limit to top 5
                        if comment['kind'] == 't1' and comment_count < 5:
                            body = comment['data'].get('body', '')
                            if body:
                                content_parts.append(f"Comment: {body}")
                                comment_count += 1

                if content_parts:
                    return ContentFetcher.clean_text('\n\n'.join(content_parts))

            return None

        except Exception as e:
            print(f"Error fetching Reddit content from {url}: {str(e)}")
            return None
