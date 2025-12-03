"""
Search stack diagnostic script.

Providers tested (if credentials available):
    1. DuckDuckGo HTML (scrape)  -> Expected: Often blocked (HTTP 202)
    2. Google Custom Search (GOOGLE_API_KEY + GOOGLE_CSE_ID)

Outputs a side-by-side PASS/FAIL matrix for each query.
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://html.duckduckgo.com/html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://duckduckgo.com/",
}

async def test_ddg_html(query: str):
    print(f"\n{'='*60}")
    print(f"Testing DuckDuckGo HTML search for: '{query}'")
    print(f"{'='*60}\n")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # Warm-up GET
            print("Step 1: Warm-up GET request...")
            try:
                warmup = await client.get(BASE_URL, headers=HEADERS)
                print(f"  ✓ Warm-up status: {warmup.status_code}")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"  ⚠ Warm-up failed: {e}")
            
            # POST search
            print("\nStep 2: POST search request...")
            data = {"q": query, "b": "", "kl": ""}
            result = await client.post(BASE_URL, data=data, headers=HEADERS)
            print(f"  ✓ POST status: {result.status_code}")
            print(f"  ✓ Content length: {len(result.text)} bytes")
            
            # Parse results
            print("\nStep 3: Parsing HTML...")
            soup = BeautifulSoup(result.text, "html.parser")
            results = soup.select(".result")
            print(f"  ✓ Found {len(results)} .result elements")
            
            if not results:
                print("\n  ⚠ No .result elements found. Checking page structure...")
                print(f"  - Title tag: {soup.title.string if soup.title else 'None'}")
                print(f"  - Body classes: {soup.body.get('class') if soup.body else 'None'}")
                
                # Try alternative selectors
                alt_results = soup.select(".web-result, .result__body, .links_main")
                print(f"  - Alternative selectors found: {len(alt_results)} items")
                
                # Show snippet of HTML
                print("\n  First 500 chars of response:")
                print(f"  {result.text[:500]}")
                return False
            
            # Display results
            print("\nStep 4: Extracting search results...")
            for i, result_elem in enumerate(results[:5], 1):
                title_elem = result_elem.select_one(".result__title")
                if not title_elem:
                    continue
                
                link_elem = title_elem.find("a")
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                link = link_elem.get("href", "")
                
                # Skip ads
                if "y.js" in link:
                    continue
                
                # Clean DDG redirect
                if "uddg=" in link:
                    try:
                        link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                    except Exception:
                        pass
                
                snippet_elem = result_elem.select_one(".result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                print(f"\n{i}. {title}")
                print(f"   URL: {link}")
                print(f"   Snippet: {snippet[:100]}...")
            
            print(f"\n{'='*60}")
            print("✓ SUCCESS: Search completed successfully!")
            print(f"{'='*60}")
            return True
            
    except httpx.TimeoutException:
        print("\n✗ ERROR: Request timed out")
        return False
    except httpx.HTTPError as e:
        print(f"\n✗ HTTP ERROR: {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_google_cse_search(query: str, max_results: int = 5):
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_ID")
    print(f"\n{'='*60}")
    print(f"Testing Google Custom Search (CSE) for: '{query}'")
    print(f"{'='*60}\n")
    if not api_key or not cx:
        print("✗ GOOGLE_API_KEY or GOOGLE_CSE_ID not set. Skipping Google test.")
        return False
    try:
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": max_results,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
            print(f"  ✓ Google status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                print("✗ No items returned by Google CSE")
                return False
            for i, item in enumerate(items[:max_results], 1):
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                print(f"\n{i}. {title}\n   URL: {link}\n   Snippet: {snippet[:120]}...")
        print(f"\n{'='*60}")
        print("✓ SUCCESS: Google CSE search completed successfully!")
        print(f"{'='*60}")
        return True
    except httpx.TimeoutException:
        print("\n✗ ERROR: Google request timed out")
        return False
    except httpx.HTTPError as e:
        print(f"\n✗ HTTP ERROR (Google): {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR (Google): {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    # Test multiple queries
    test_queries = [
        "python programming",
        "current gold price",
        "internet of things",
        "relationship between Gensol and Go-Auto"
    ]
    
    results = {}
    for query in test_queries:
        ddg_success = await test_ddg_html(query)
        cse_success = await test_google_cse_search(query)
        results[query] = (
            f"DDG_HTML: {'✓' if ddg_success else '✗'} | GoogleCSE: {'✓' if cse_success else '✗'}"
        )
        await asyncio.sleep(1)  # Pause between requests
    
    # Summary
    print(f"\n\n{'='*60}")
    print("SEARCH TEST SUMMARY")
    print(f"{'='*60}")
    for query, status in results.items():
        print(f"{status} :: {query}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())
