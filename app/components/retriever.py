from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from app.components.llm import load_llm
from app.components.vector_store import load_vector_store

from app.common.logger import get_logger
from app.common.custom_exception import CustomException

logger = get_logger(__name__)

CUSTOM_PROMPT_TEMPLATE = """Answer the following medical question in 4-5 lines maximum using only the information provided in the context.
If the context does not contain the answer, say "I don't have enough information to answer that."

Context:
{context}

Question:
{question}

Answer:
"""


def set_custom_prompt():
    return ChatPromptTemplate.from_messages([
        ("system", "You are a concise medical assistant."),
        ("human", CUSTOM_PROMPT_TEMPLATE),
    ])


def format_docs(docs):
    """Combines retrieved Document objects into a single string context."""
    return "\n\n".join(doc.page_content for doc in docs)


def create_qa_chain():
    try:
        logger.info("Loading vector store for context")
        db = load_vector_store()

        if db is None:
            raise CustomException("Vector store not present or empty")

        llm = load_llm()

        if llm is None:
            raise CustomException("LLM not loaded")

        
        retriever = db.as_retriever(search_kwargs={"k": 3})
        prompt = set_custom_prompt()

        qa_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough(),
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        logger.info("Successfully created the QA chain")
        return qa_chain

    except Exception as e:
        error_message = CustomException("Failed to make a QA chain", e)
        logger.error(str(error_message))
        return None



_qa_chain = None


def get_qa_chain():
    global _qa_chain
    if _qa_chain is None:
        _qa_chain = create_qa_chain()  
    return _qa_chain