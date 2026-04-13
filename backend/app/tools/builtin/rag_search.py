from langchain_core.tools import tool
from loguru import logger


@tool
def rag_search(query: str) -> str:
    """Search the knowledge base for relevant documents and information."""
    try:
        from app.rag.retriever import get_retriever

        retriever = get_retriever()
        if retriever is None:
            return "RAG is not enabled or configured."

        docs = retriever.invoke(query)
        if not docs:
            return "No relevant documents found in the knowledge base."

        results = "Knowledge base results:\n"
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Unknown")
            results += f"\n{i}. [Source: {source}]\n{doc.page_content[:500]}\n"
        return results
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return f"Error searching knowledge base: {e}"
