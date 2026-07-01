import os
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


def web_search(query: str) -> str:
    """Search the web with Tavily and return titles, URLs and snippets."""
    if not tavily:
        return "Web search is not configured (missing TAVILY_API_KEY)."
    try:
        results = tavily.search(query=query, max_results=5)
    except Exception as exc:
        return f"Search error: {exc}"

    out = []
    for r in results.get("results", []):
        out.append(
            f"Title: {r.get('title', '')}\n"
            f"URL: {r.get('url', '')}\n"
            f"Snippet: {(r.get('content') or '')[:400]}"
        )
    return "\n\n".join(out) if out else "No results found."


def scrape_url(url: str) -> str:
    """Fetch a URL and return its main readable text content."""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:4000] if text else "No readable text found on this page."
    except Exception as exc:
        return f"Error scraping URL: {exc}"

# Tool schemas in the format the Mistral chat completions API expects.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the live web for current, recent, or factual information "
                "you do not already know confidently. Use this whenever the user "
                "asks about recent events, current data, specific facts you are "
                "unsure of, or explicitly asks you to look something up."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": (
                "Fetch and read the full text content of a specific web page URL. "
                "Use this after web_search when you need more detail than the "
                "snippet gives you, or when the user gives you a direct link."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch.",
                    }
                },
                "required": ["url"],
            },
        },
    },
]

TOOL_IMPLEMENTATIONS = {
    "web_search": web_search,
    "scrape_url": scrape_url,
}
