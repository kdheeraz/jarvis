from ddgs import DDGS
from loguru import logger
from langchain.tools import tool


tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current information, news, weather, stock prices, and other real-time data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find information about"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]


@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Perform a web search and return formatted results."""
    try:
        print(f"Performing web search for query: '{query}' with max_results={max_results}")
        ddgs = DDGS()
        results = ddgs.text(query, max_results=max_results)
        if not results:
            return "No search results found."
        
        formatted_results = "Search results:\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"\n{i}. {result.get('title', 'No title')}\n"
            formatted_results += f"   {result.get('body', 'No description')}\n"
        return formatted_results
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return "Unable to perform web search at the moment."



