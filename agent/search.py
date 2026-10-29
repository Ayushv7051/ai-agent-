"""
Provider-independent Web Search and Research Engine for Ayush AI.
Abstracts the search provider so DuckDuckGo, Bing, Google, or SearXNG can be swapped in.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from agent.logger import logger


class BaseSearchProvider(ABC):
    """Abstract search provider interface."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Executes a search query and returns structured results:
        [{"title": ..., "url": ..., "description": ...}]
        """
        pass


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """DuckDuckGo provider implementation using DDGS."""

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        try:
            logger.info(f"Executing DDGS web search for query: '{query}' (max_results={max_results})")
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                for item in ddg_results:
                    title = item.get("title", "").strip()
                    url = item.get("href", item.get("link", "")).strip()
                    desc = item.get("body", item.get("snippet", "")).strip()
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url,
                            "description": desc
                        })
            logger.info(f"DDGS returned {len(results)} results.")
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            results.append({
                "title": "Search Error",
                "url": "",
                "description": f"Failed to retrieve live web results due to network or provider error: {str(e)}"
            })
        return results


# Default provider instance (can be swapped at runtime or via config)
_current_provider: BaseSearchProvider = DuckDuckGoSearchProvider()


def get_search_provider() -> BaseSearchProvider:
    return _current_provider


def set_search_provider(provider: BaseSearchProvider) -> None:
    global _current_provider
    _current_provider = provider


def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Standard web search tool returning structured results."""
    provider = get_search_provider()
    return provider.search(query=query, max_results=max_results)


def web_research(topic: str, max_sources: int = 3) -> Dict[str, Any]:
    """
    Conducts in-depth web research on a topic, extracting summaries and source links.
    Clearly marks information retrieved directly from the live web.
    """
    logger.info(f"Starting web research on: '{topic}'")
    results = web_search(query=topic, max_results=max_sources)

    if not results or (len(results) == 1 and results[0].get("title") == "Search Error"):
        return {
            "status": "partial_error",
            "topic": topic,
            "summary": "Could not fetch online research due to a connection issue.",
            "sources": []
        }

    sources = []
    summary_points = []
    for idx, r in enumerate(results, 1):
        sources.append({
            "index": idx,
            "title": r.get("title"),
            "url": r.get("url")
        })
        desc = r.get("description", "").strip()
        if desc:
            summary_points.append(f"[{idx}] {r.get('title')}: {desc}")

    formatted_summary = "\n".join(summary_points) if summary_points else "No detailed snippets found."

    return {
        "status": "success",
        "topic": topic,
        "web_retrieved_data": formatted_summary,
        "sources": sources,
        "notice": "All findings above were retrieved from live web search."
    }
