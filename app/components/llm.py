from langchain_groq import ChatGroq
from app.config.config import GROQ_API_KEY, GROQ_MODEL

from app.common.logger import get_logger
from app.common.custom_exception import CustomException

logger = get_logger(__name__)


def load_llm(model: str = GROQ_MODEL, api_key: str = GROQ_API_KEY):
    try:
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")

        logger.info("Loading LLM from Groq")

        chat_model = ChatGroq(
            model=model,
            api_key=api_key,
            temperature=0.2,
            max_tokens=1024,
            reasoning_effort="low",
        )

        logger.info("LLM loaded successfully...")
        return chat_model

    except Exception as e:
        error_message = CustomException("Failed to load a llm", e)
        logger.error(str(error_message))
        return None