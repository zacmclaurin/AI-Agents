"""Web search tools — DuckDuckGo, no API key required."""

from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from duckduckgo_search import DDGS


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query")
    max_results: int = Field(5, description="Number of results to return (default 5)")


class DuckDuckGoSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web using DuckDuckGo. Use this to find current information, "
        "research topics, look up documentation, or find anything that requires "
        "up-to-date knowledge beyond your training data."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r['title']}\n   {r['href']}\n   {r['body']}")
            return "\n\n".join(lines)
        except Exception as e:
            return f"Search error: {e}"


SEARCH_TOOLS = [DuckDuckGoSearchTool()]
