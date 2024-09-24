import json
import os
import re
from typing import List, Union

import nltk
import spacy
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pydantic import BaseModel, Field
from spacy.lang.en.stop_words import STOP_WORDS

from app.utils.llms import pro_query_llm as llm

# nltk.download('punkt')
# nltk.download('stopwords')


class LLMOutput(BaseModel):
    refined_query: Union[str, List[str]] = Field(
        ..., description="The refined query as a string or list of words")


structured_llm = llm.with_structured_output(LLMOutput)


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
    Task: Further refine the query to be more specific and searchable in a vector database, while staying true to the original intent. Focus on key concepts and technical terms. Respond in JSON format with key as 'refined_query' ONLY
    """
        else:
            prompt = refined_query
        improved_query = structured_llm.invoke(prompt)
        return improved_query.refined_query
    except Exception as e:
        print(f"Error in improve_query: {str(e)}")
        return query


nlp = spacy.load("en_core_web_sm")

CUSTOM_STOP_WORDS = STOP_WORDS.copy()
CUSTOM_STOP_WORDS.discard('name')  # Keep 'name' as it might be important in


def preprocess_query2(query, context=""):
    doc = nlp(query.lower())

    # Extract tokens while removing custom stop words and punctuation
    tokens = [
        token.lemma_ for token in doc if token.text not in CUSTOM_STOP_WORDS and not token.is_punct]

    # Preserve named entities and multi-word expressions
    for chunk in doc.noun_chunks:
        if not all(token.is_stop for token in chunk):
            tokens.append(chunk.lemma_)

    # Add context-specific terms
    context_doc = nlp(context.lower())
    context_terms = [ent.text for ent in context_doc.ents if ent.label_ in [
        'ORG', 'PRODUCT', 'TECH']]
    tokens.extend([term for term in context_terms if term in query.lower()])

    # Remove duplicates and join
    processed_query = " ".join(list(dict.fromkeys(tokens)))

    return processed_query
