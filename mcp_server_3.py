from mcp.server.fastmcp import FastMCP, Context
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import re
from models import SearchInput, UrlInput
from models import PythonCodeOutput  # Import the models we need
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class SearchResult:
    title: str
    link: str
    snippet: str
    position: int


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [
            req for req in self.requests if now - req < timedelta(minutes=1)
        ]

        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.requests.append(now)


class DuckDuckGoSearcher:
    BASE_URL = "https://html.duckduckgo.com/html"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/",
    }

    def __init__(self):
        self.rate_limiter = RateLimiter()
        # Google Custom Search API requires both API key and CX (search engine id)
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cx = os.getenv("GOOGLE_CSE_ID")
        # (SerpAPI disabled for now; using pure Google Custom Search)
        self.serpapi_key = None  # previously: os.getenv("SERPAPI_KEY")

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            return "No results were found for your search query. The query may not have returned any matches. Please try rephrasing your search."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for result in results:
            output.append(f"{result.position}. {result.title}")
            output.append(f"   URL: {result.link}")
            output.append(f"   Summary: {result.snippet}")
            output.append("")  # Empty line between results

        return "\n".join(output)

    async def search(
        self, query: str, ctx: Context, max_results: int = 10
    ) -> List[SearchResult]:
        try:
            # Use Google Custom Search API exclusively
            if not self.google_api_key or not self.google_cx:
                await ctx.error("Google API credentials not configured. Please set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")
                return []
            
            await ctx.info("Using Google Custom Search API for web search")
            params = {
                "key": self.google_api_key,
                "cx": self.google_cx,
                "q": query,
                "num": max_results,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                results: List[SearchResult] = []
                for i, item in enumerate(items, start=1):
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            link=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                            position=i,
                        )
                    )
                    if len(results) >= max_results:
                        break
                if results:
                    await ctx.info(f"Successfully found {len(results)} results via Google CSE")
                    return results
                else:
                    await ctx.info("Google CSE returned no results for this query")
                    return []

        except httpx.TimeoutException:
            await ctx.error("Search request timed out")
            return []
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred: {str(e)}")
            return []
        except Exception as e:
            await ctx.error(f"Unexpected error during search: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            return []


class WebContentFetcher:
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    async def fetch_and_parse(self, url: str, ctx: Context) -> str:
        """Fetch and parse content from a webpage"""
        try:
            await self.rate_limiter.acquire()

            await ctx.info(f"Fetching content from: {url}")

            async with httpx.AsyncClient() as client:
                result = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    follow_redirects=True,
                    timeout=30.0,
                )
                result.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(result.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            # Get the text content
            text = soup.get_text()

            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text).strip()

            # Truncate if too long
            if len(text) > 8000:
                text = text[:8000] + "... [content truncated]"

            await ctx.info(
                f"Successfully fetched and parsed content ({len(text)} characters)"
            )
            return text

        except httpx.TimeoutException:
            await ctx.error(f"Request timed out for URL: {url}")
            return "Error: The request timed out while trying to fetch the webpage."
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred while fetching {url}: {str(e)}")
            return f"Error: Could not access the webpage ({str(e)})"
        except Exception as e:
            await ctx.error(f"Error fetching content from {url}: {str(e)}")
            return f"Error: An unexpected error occurred while fetching the webpage ({str(e)})"


# Initialize FastMCP server
mcp = FastMCP("ddg-search")
searcher = DuckDuckGoSearcher()
fetcher = WebContentFetcher()


@mcp.tool()
async def duckduckgo_search_results(input: SearchInput, ctx: Context) -> str:
    """Search the web using Google Custom Search API. Usage: input={"input": {"query": "latest AI developments", "max_results": 5} } result = await mcp.call_tool('duckduckgo_search_results', input)"""
    try:
        results = await searcher.search(input.query, ctx, input.max_results)
        return PythonCodeOutput(result=searcher.format_results_for_llm(results))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"


@mcp.tool()
async def download_raw_html_from_url(input: UrlInput, ctx: Context) -> str:
    """Fetch webpage content. Usage: input={"input": {"url": "https://example.com"} } result = await mcp.call_tool('download_raw_html_from_url', input)"""
    return PythonCodeOutput(result=await fetcher.fetch_and_parse(input.url, ctx))


if __name__ == "__main__":
    print("mcp_server_3.py starting")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
            mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
        print("\nShutting down...")