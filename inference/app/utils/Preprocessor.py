import re
from typing import List

from app.utils.llms import pro_query_llm

# from spacy.lang.en.stop_words import STOP_WORDS


STOP_WORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
    'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how'
}


def tokenize(text: str) -> List[str]:
    """Simple tokenization by splitting on whitespace and removing punctuation"""
    # Convert to lowercase and remove punctuation
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.split()


def basic_stem(word: str) -> str:
    """Basic stemming rules"""
    if len(word) < 4:  # Don't stem very short words
        return word

    if word.endswith('ing'):
        return word[:-3]
    elif word.endswith('ed'):
        return word[:-2]
    elif word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    elif word.endswith('ly'):
        return word[:-2]
    return word


def preprocess_query(query: str, context: str = "") -> str:
    """Preprocess the query by tokenizing and removing stop words"""
    # Tokenize
    tokens = tokenize(query)

    # Remove stop words
    tokens = [token for token in tokens if token not in STOP_WORDS]

    # Join tokens back into a string
    return ' '.join(tokens)


def prepare_fulltext_query(natural_query: str) -> str:
    """Prepare query for PostgreSQL full-text search"""
    # Tokenize and clean
    tokens = tokenize(natural_query)

    # Remove stop words
    tokens = [token for token in tokens if token not in STOP_WORDS]

    # Apply basic stemming
    tokens = [basic_stem(token) for token in tokens]

    # Create PostgreSQL full-text search query
    if not tokens:
        return ""

    # Join with boolean operators and add wildcards
    query_terms = [f"{token}:*" for token in tokens]
    return ' & '.join(query_terms)


def improve_query(query: str, refined_query: str, context: str = "", want_to_update: bool = False) -> str:
    """Improve query using LLM"""
    try:
        if want_to_update:
            prompt = f"""
    Original: {query}
    Initial Refinement: {refined_query}
    {context}
    Task: Further refine the query to be more specific and searchable in a vector database, while staying true to the original intent. Focus on key concepts and technical terms.
    """
        else:
            prompt = refined_query

        improved_query = pro_query_llm.invoke(prompt)
        return improved_query.content
    except Exception as e:
        print(f"Error in improve_query: {str(e)}")
        return query
