import re
from typing import List, Union

import nltk
import spacy
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from pydantic import BaseModel, Field
from spacy.lang.en.stop_words import STOP_WORDS

from app.utils.llms import pro_query_llm


def preprocess_query(query: str, context: str = "") -> str:
    # Convert to lowercase
    query = query.lower()

    # Remove special characters
    query = re.sub(r'[^\w\s]', '', query)

    # Tokenize
    tokens = word_tokenize(query)

    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]

    # Join tokens back into a string
    preprocessed_query = ' '.join(tokens)

    return preprocessed_query


def improve_query(query: str, refined_query: str, context: str = "", wantToUpdate: bool = False) -> str:
    try:
        if wantToUpdate:
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


nlp = spacy.load("en_core_web_sm")

CUSTOM_STOP_WORDS = STOP_WORDS.copy()
CUSTOM_STOP_WORDS.discard('name')  # Keep 'name' as it might be important in


nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')


def prepare_fulltext_query(natural_query):
    # Tokenize
    tokens = nltk.word_tokenize(preprocess_query(natural_query.lower()))

    # Remove stop words
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]

    # Stemming
    stemmer = PorterStemmer()
    tokens = [stemmer.stem(token) for token in tokens]

    # Add boolean operators and wildcards
    query = ' AND '.join(tokens)
    query = query.replace(' AND ', '* AND ') + '*'

    return query
