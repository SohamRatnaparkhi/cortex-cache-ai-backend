import os

import google.generativeai as genai
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI

if os.path.exists(".env"):
    load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPEN_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

XAI_API_KEY = os.getenv("XAI_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["OPENAI_API_KEY"] = OPEN_API_KEY
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
os.environ["XAI_API_KEY"] = XAI_API_KEY
os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

summary_llm = ChatOpenAI(
    api_key=OPEN_API_KEY,
    model_name="gpt-4o-mini",
    max_retries=3,
    timeout=None,
    temperature=0.3,
    max_tokens=1800,
)

pro_query_llm = ChatOpenAI(
    api_key=OPEN_API_KEY,
    model_name="gpt-4o-mini",
    max_retries=3,
    timeout=None,
    temperature=0.3,
    max_tokens=1800,
)

memory_search_query_llm = ChatGroq(
    model="gpt-4o-mini",
    temperature=0.1,
    max_tokens=500,
    timeout=None,
    max_retries=3,
)

gemini_generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-8b",
    generation_config=gemini_generation_config,
)
gemini_model_pro = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=gemini_generation_config,
)


def get_answer_llm(llm_name: str = 'gpt-4o', is_pro: bool = False):
    if not is_pro:
        return ChatGroq(
            model="llama-3.1-70b-versatile",
            temperature=0.7,
            max_tokens=1000,
            timeout=None,
            max_retries=3,
        )
    if llm_name == 'grok':
        return ChatXAI(
            api_key=XAI_API_KEY,
            model_name="grok-2-latest",
            max_retries=3,
            timeout=None,
            temperature=0.4,
            max_tokens=3500,
        )
    if llm_name == 'gemini-pro':
        return ChatGoogleGenerativeAI(
            model="gemini-1-5-pro",
            max_retries=3,
            timeout=None,
            temperature=0.4,
            max_tokens=3500,
        )
    if llm_name == 'gemini-flash':
        return ChatGoogleGenerativeAI(
            model="gemini-1-5-flash",
            max_retries=3,
            timeout=None,
            temperature=0.4,
            max_tokens=3500,
        )
    if llm_name == 'gpt-4o':
        return ChatOpenAI(
            api_key=OPEN_API_KEY,
            model_name="gpt-4o",
            max_retries=3,
            timeout=None,
            temperature=0.4,
            max_tokens=3500,
        )
    if llm_name == 'sonnet-3.5':
        return ChatAnthropic(
            api_key=ANTHROPIC_API_KEY,
            model="claude-3-5-sonnet-20241022",
            max_tokens=3500,
            temperature=0.4,
            max_retries=3,
        )
    if llm_name == 'llama-3.1-70b':
        return ChatGroq(
            model="llama-3.1-70b-versatile",
            temperature=0.4,
            max_tokens=1800,
            timeout=None,
            max_retries=3,
        )
    if llm_name == 'gpt-4o-mini':
        return ChatOpenAI(
            api_key=OPEN_API_KEY,
            model_name="gpt-4o-mini",
            max_retries=3,
            timeout=None,
            temperature=0.4,
            max_tokens=1800,
        )
    if llm_name == 'llama-3.2-3b':
        return ChatGroq(
            model="llama-3.2-3b-preview",
            temperature=0.1,
            max_tokens=1000,
            timeout=None,
            max_retries=3,
        )

    if llm_name == 'llama-3.2-90b':
        return ChatGroq(
            model="llama-3.2-90b",
            temperature=0.7,
            max_tokens=1000,
            timeout=None,
            max_retries=3,
        )


free_query_llm = ChatGroq(
    model="llama-3.1-70b-versatile",
    temperature=1,
    max_tokens=500,
    timeout=None,
    max_retries=3,
)

answer_llm_free = ChatGroq(
    model="llama-3.1-70b-versatile",
    temperature=0.7,
    max_tokens=1000,
    timeout=None,
    max_retries=3,
)
