#!/usr/bin/env python3
"""
FastAPI server with a persistent cache for selectors, page types, and field selectors.

- POST /scrape {"url": "..."}
  - Checks cache for the URL's domain.
  - Cache Hit: Runs scrape with the cached selector and field selectors (fast).
  - Cache Miss: Runs full LLM-based scrape (slow) and saves the result to the cache.
"""

import uvicorn
import json
import os
import aiofiles
import asyncio
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

# --- Import the core scraping logic ---
try:
    from AdaptiveProductSearcher import scrape
except ImportError:
    print("Error: Make sure 'AdaptiveProductSearcher.py' is in the same directory.")
    exit(1)

# --- Cache Setup ---
CACHE_FILE = "selector_cache.json"
site_cache: Dict[str, Dict[str, Any]] = {}
cache_lock = asyncio.Lock()


def get_domain_key(url: str) -> str:
    """Extracts the 'netloc' (e.g., 'eu.aimeleondore.com') as the cache key."""
    try:
        return urlparse(url).netloc
    except Exception:
        return url.split("//")[-1].split("/")[0]


async def load_cache():
    """Loads the cache from the JSON file into memory."""
    global site_cache
    if os.path.exists(CACHE_FILE):
        print(f"Loading cache from {CACHE_FILE}...")
        try:
            async with aiofiles.open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                site_cache = json.loads(content)
                print(f"✅ Cache loaded with {len(site_cache)} entries.")
        except Exception as e:
            print(f"⚠️ Could not load cache: {e}")
            site_cache = {}
    else:
        print("No cache file found, starting fresh.")
        site_cache = {}


async def save_cache():
    """Saves the in-memory cache back to the JSON file."""
    async with cache_lock:
        try:
            async with aiofiles.open(CACHE_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(site_cache, indent=2))
                print(f"✅ Cache saved to {CACHE_FILE}.")
        except Exception as e:
            print(f"⚠️ Could not save cache: {e}")


# --- API Setup ---
app = FastAPI(
    title="Adaptive Product Search API",
    description="A cache-aware API to scrape product information with enhanced field extraction.",
    version="2.0.0",
)


@app.on_event("startup")
async def on_startup():
    """Load the persistent cache when the server starts."""
    await load_cache()


# --- Request and Response Models ---
class Product(BaseModel):
    """Enhanced product model with all new fields."""

    name: str
    url: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    in_stock: Optional[bool] = None


class ScrapeRequest(BaseModel):
    """The JSON request body for the /scrape endpoint."""

    url: HttpUrl


class ScrapeResponse(BaseModel):
    """The JSON response body from the /scrape endpoint with all new fields."""

    url: str
    platform: str
    page_type: str
    selector: Optional[str] = None
    field_selectors: Optional[Dict[str, List[str]]] = None
    products: List[Product]
    cache_status: str


# --- API Endpoint ---
@app.post("/scrape", response_model=ScrapeResponse)
async def run_scrape(request: ScrapeRequest) -> Dict[str, Any]:
    """
    Asynchronously run the web scraper, using a cache for selectors, page types, and field selectors.
    """
    url_str = str(request.url)
    domain_key = get_domain_key(url_str)
    print(f"API: Received scrape request for: {url_str} (Domain: {domain_key})")

    cached_data = site_cache.get(domain_key)
    cache_status = "MISS"
    result: Dict[str, Any]

    try:
        if cached_data:
            # --- CACHE HIT ---
            cache_status = "HIT"
            print(f"⚡ Cache HIT for {domain_key}.")
            print(f"   Selector: {cached_data.get('selector')}")
            print(f"   Page Type: {cached_data.get('page_type')}")
            print(
                f"   Field Selectors: {list(cached_data.get('field_selectors', {}).keys())}"
            )

            result = await scrape(
                url_str,
                cached_selector=cached_data.get("selector"),
                cached_page_type=cached_data.get("page_type"),
                cached_field_selectors=cached_data.get("field_selectors"),
                headless=True,
            )
        else:
            # --- CACHE MISS ---
            cache_status = "MISS"
            print(f"🐌 Cache MISS for {domain_key}. Running full LLM discovery...")
            result = await scrape(url_str, headless=True)

            # --- Update Cache on Successful Scrape ---
            if result.get("selector") and result.get("page_type"):
                new_cache_entry = {
                    "selector": result["selector"],
                    "page_type": result["page_type"],
                    "field_selectors": result.get("field_selectors"),
                    "created_at": time.time(),
                }
                site_cache[domain_key] = new_cache_entry
                print(f"💾 Saving new cache entry for {domain_key}.")
                await save_cache()

        num_products = len(result.get("products", []))
        print(
            f"API: Scraping for {url_str} finished. Found {num_products} products (Cache: {cache_status})."
        )

        # Print sample product info for debugging
        if num_products > 0:
            sample = result["products"][0]
            print(f"📦 Sample product fields:")
            print(f"   Name: {sample.get('name', 'N/A')}")
            print(f"   Price: {sample.get('price', 'N/A')}")
            print(f"   Image: {'Yes' if sample.get('image_url') else 'No'}")
            print(f"   Description: {'Yes' if sample.get('description') else 'No'}")
            print(f"   In Stock: {sample.get('in_stock', 'N/A')}")

        result["cache_status"] = cache_status
        return result

    except asyncio.TimeoutError:
        print(f"API Error: Scraping timed out for {url_str}")
        raise HTTPException(status_code=504, detail="Scraping process timed out.")
    except Exception as e:
        print(f"API Error: An unexpected error occurred for {url_str}: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


# --- Additional endpoints for cache management ---
@app.get("/cache/status")
async def get_cache_status():
    """Get cache statistics and status."""
    return {
        "total_domains": len(site_cache),
        "domains": list(site_cache.keys()),
        "cache_file": CACHE_FILE,
        "cache_file_exists": os.path.exists(CACHE_FILE),
    }


@app.delete("/cache/{domain}")
async def clear_cache_domain(domain: str):
    """Clear cache for a specific domain."""
    if domain in site_cache:
        del site_cache[domain]
        await save_cache()
        return {"message": f"Cache cleared for domain: {domain}"}
    else:
        raise HTTPException(
            status_code=404, detail=f"Domain not found in cache: {domain}"
        )


@app.delete("/cache")
async def clear_all_cache():
    """Clear all cache entries."""
    global site_cache
    site_cache = {}
    await save_cache()
    return {"message": "All cache entries cleared"}


# --- Run the server ---
if __name__ == "__main__":
    print("Starting FastAPI server on http://0.0.0.0:8000")
    print("Enhanced version with improved selector discovery")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
