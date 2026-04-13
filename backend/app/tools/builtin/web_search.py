from ddgs import DDGS
from langchain_core.tools import tool
from loguru import logger


@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Search the web for current information, news, weather, and other real-time data."""
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=max_results)
        if not results:
            return "No search results found."

        formatted = "Search results:\n"
        for i, result in enumerate(results, 1):
            formatted += f"\n{i}. {result.get('title', 'No title')}\n"
            formatted += f"   {result.get('body', 'No description')}\n"
            formatted += f"   URL: {result.get('href', '')}\n"
        return formatted
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Unable to perform web search: {e}"
