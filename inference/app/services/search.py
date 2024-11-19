from dataclasses import dataclass
from typing import List, Optional, TypedDict
from urllib.parse import urljoin, urlparse, urlunparse

import requests

from app.schemas.web_agent import SearchResponse, SearxngSearchOptions


def search_searxng(
    query: str,
    opts: Optional[SearxngSearchOptions] = None,
    limit: int = 15
) -> SearchResponse:
    """
    Search using SearxNG API.

    Args:
        query: Search query string
        opts: Optional search parameters including categories, engines, language, and page number

    Returns:
        SearchResponse object containing results and suggestions
    """
    # Get the base URL from config
    searxng_url = "http://localhost:8080"

    # Parse and reconstruct the URL to ensure proper formatting
    parsed_url = urlparse(searxng_url)
    base_url = urlunparse(parsed_url)

    # Construct the search URL
    url = urljoin(base_url, "/search")

    # Initialize parameters with the required ones
    params = {
        'q': query,
        'format': 'json'
    }

    # Add optional parameters if provided
    if opts:
        for key, value in opts.items():
            if isinstance(value, list):
                params[key] = ','.join(value)
            else:
                params[key] = value

    try:
        # Make the request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the response
        data = response.json()

        # Extract results and suggestions
        results = data.get('results', [])[0: limit]
        suggestions = data.get('suggestions', [])

        return SearchResponse(results=results, suggestions=suggestions)

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making request to SearxNG API: {str(e)}")
    except ValueError as e:
        raise Exception(f"Error parsing JSON response: {str(e)}")
