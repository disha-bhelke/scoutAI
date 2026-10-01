from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import settings


RAG_PROMPT_TEMPLATE = """You are Scout AI, a RAG assistant.

Answer the question strictly using the context below and taking into account the previous conversation history if relevant. Be concise for simple factual questions, and detailed when an explanation or procedure is needed. If the answer cannot be determined from the context, say: "I cannot find the answer in the provided document context."

Conversation History:
{chat_history}

Context:
{context}

Question:
{question}

Answer:"""


class AnswerGenerator:
    """Generates grounded answers based on retrieved document context and chat history using Gemini LLM."""

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = (api_key or settings.GEMINI_API_KEY).strip()
        self.model_name = model_name or settings.LLM_MODEL

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please provide it in .env or environment variables."
            )

        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.2
        )
        self.prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        self.chain = self.prompt | self.llm | StrOutputParser()

    def generate_answer(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        chat_history: str = "No previous conversation history."
    ) -> str:
        """
        Formats retrieved context chunks and chat history, then generates a grounded response.
        """
        if not context_chunks:
            return "No relevant context found in the document to answer your question."

        formatted_contexts = []
        for i, chunk in enumerate(context_chunks, 1):
            formatted_contexts.append(
                f"[Source {i} | Doc: {chunk.get('document_name')} | Page: {chunk.get('page_number')} | Chunk ID: {chunk.get('chunk_id')}]\n{chunk.get('content')}"
            )

        combined_context = "\n\n---\n\n".join(formatted_contexts)
        answer = self.chain.invoke({
            "chat_history": chat_history or "No previous conversation history.",
            "context": combined_context,
            "question": query
        })
        return answer.strip()
