#!/usr/bin/env python3
"""
FastAPI server with a persistent cache for selectors and page types.

- POST /scrape {"url": "..."}
  - Checks cache for the URL's domain.
  - Cache Hit: Runs scrape with the cached selector (fast).
  - Cache Miss: Runs full LLM-based scrape (slow) and saves the result to the cache.
"""

import uvicorn
import json
import os
import aiofiles
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
from urllib.parse import urlparse

# --- Import the core scraping logic ---
try:
    from AdaptiveProductSearcher import scrape
except ImportError:
    print("Error: Make sure 'AdaptiveProductSearcher.py' is in the same directory.")
    exit(1)

# --- Cache Setup ---
CACHE_FILE = "selector_cache.json"
# In-memory cache, loaded from file
site_cache: Dict[str, Dict[str, str]] = {}
# A lock to prevent race conditions when writing to the cache file
cache_lock = asyncio.Lock()


def get_domain_key(url: str) -> str:
    """Extracts the 'netloc' (e.g., 'eu.aimeleondore.com') as the cache key."""
    try:
        return urlparse(url).netloc
    except Exception:
        # Fallback for weird URLs
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
    description="A cache-aware API to scrape product information.",
    version="1.2.0",
)


@app.on_event("startup")
async def on_startup():
    """Load the persistent cache when the server starts."""
    await load_cache()


# --- Request and Response Models ---
class ScrapeRequest(BaseModel):
    """The JSON request body for the /scrape endpoint."""

    url: HttpUrl


class ScrapeResponse(BaseModel):
    """The JSON response body from the /scrape endpoint."""

    url: str
    platform: str
    page_type: str
    selector: str | None
    products: list
    cache_status: str  # Added for clarity


# --- API Endpoint ---
@app.post("/scrape")
async def run_scrape(request: ScrapeRequest) -> Dict[str, Any]:
    """
    Asynchronously run the web scraper, using a cache for selectors and page types.
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
            print(
                f"⚡ Cache HIT for {domain_key}. Using selector: {cached_data.get('selector')}"
            )
            result = await scrape(
                url_str,
                cached_selector=cached_data.get("selector"),
                cached_page_type=cached_data.get("page_type"),
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
                }
                site_cache[domain_key] = new_cache_entry
                print(f"💾 Saving new cache entry for {domain_key}.")
                await save_cache()

        num_products = len(result.get("products", []))
        print(
            f"API: Scraping for {url_str} finished. Found {num_products} products (Cache: {cache_status})."
        )

        result["cache_status"] = cache_status
        return result

    except asyncio.TimeoutError:
        print(f"API Error: Scraping timed out for {url_str}")
        raise HTTPException(status_code=504, detail="Scraping process timed out.")
    except Exception as e:
        print(f"API Error: An unexpected error occurred for {url_str}: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


# --- Run the server ---
if __name__ == "__main__":
    print("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
