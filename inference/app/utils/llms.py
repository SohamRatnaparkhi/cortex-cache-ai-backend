import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

load_dotenv()

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPEN_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["OPENAI_API_KEY"] = OPEN_API_KEY
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

summary_llm = ChatGroq(
    model="llama-3.2-3b-preview",
    temperature=0.4,
    max_tokens=500,
    timeout=None,
    max_retries=5,
)

# pro_query_llm = ChatGroq(
#     model="llama-3.2-3b-preview",
#     temperature=0.1,
#     max_tokens=1000,
#     timeout=None,
#     max_retries=3,
# )

pro_query_llm = ChatOpenAI(
    api_key=OPEN_API_KEY,
    model_name="gpt-4o-mini",
    max_retries=3,
    timeout=None,
    temperature=0.7,
    max_tokens=1800,
)

memory_search_query_llm = ChatGroq(
    model="llama-3.2-3b-preview",
    temperature=0.1,
    max_tokens=500,
    timeout=None,
    max_retries=3,
)

# answer_llm_pro = ChatAnthropic(
#     api_key=ANTHROPIC_API_KEY,
#     model_name="claude-3-5-sonnet-20241022",
#     max_tokens=5000,
#     temperature=1,
#     timeout=None,
#     max_retries=3,
# )

# answer_llm_pro = ChatGroq(
#     model="llama-3.1-70b-versatile",
#     temperature=0.7,
#     max_tokens=1800,
#     timeout=None,
#     max_retries=3,
# )

answer_llm_pro = ChatOpenAI(
    api_key=OPEN_API_KEY,
    model_name="gpt-4o",
    max_retries=3,
    timeout=None,
    temperature=0.4,
    max_tokens=1800,
)

# answer_llm_pro = ChatOpenAI(
#     api_key=OPEN_API_KEY,
#     model_name="o1-mini",
#     max_retries=3,
#     timeout=None,
#     temperature=0.7,
#     max_tokens=1800,
# )

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
