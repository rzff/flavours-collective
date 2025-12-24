#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiofiles
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

# --- Robust Path Handling ---
# Get the directory where THIS script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Add that directory to sys.path so 'import AdaptiveProductSearcher' works
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

CACHE_FILE = os.path.join(BASE_DIR, "selector_cache.json")

# --- Import core logic AFTER path setup ---
try:
    from AdaptiveProductSearcher import scrape
except ImportError:
    print(f"Error: Could not find 'AdaptiveProductSearcher.py' in {BASE_DIR}")
    sys.exit(1)

# --- Cache State ---
site_cache: Dict[str, Dict[str, Any]] = {}
cache_lock = asyncio.Lock()


def get_domain_key(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return url.split("//")[-1].split("/")[0]


async def load_cache():
    global site_cache
    if os.path.exists(CACHE_FILE):
        try:
            async with aiofiles.open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                site_cache = json.loads(content)
                print(
                    f"✅ Cache loaded with {len(site_cache)} entries from {CACHE_FILE}."
                )
        except Exception as e:
            print(f"⚠️ Could not load cache: {e}")
            site_cache = {}
    else:
        print(f"No cache file found at {CACHE_FILE}, starting fresh.")
        site_cache = {}


async def save_cache():
    async with cache_lock:
        try:
            async with aiofiles.open(CACHE_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(site_cache, indent=2))
                print(f"✅ Cache saved to {CACHE_FILE}.")
        except Exception as e:
            print(f"⚠️ Could not save cache: {e}")


# --- Lifespan Manager (Modern replacement for on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await load_cache()
    yield
    # Shutdown logic (optional)
    print("Shutting down...")


app = FastAPI(
    title="Adaptive Product Search API",
    lifespan=lifespan,
    version="2.0.0",
)


# --- Request/Response Models ---
class Product(BaseModel):
    name: str
    url: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    in_stock: Optional[bool] = None


class ScrapeRequest(BaseModel):
    url: HttpUrl


class ScrapeResponse(BaseModel):
    url: str
    platform: str
    page_type: str
    selector: Optional[str] = None
    field_selectors: Optional[Dict[str, List[str]]] = None
    products: List[Product]
    cache_status: str


@app.post("/scrape", response_model=ScrapeResponse)
async def run_scrape(request: ScrapeRequest):
    url_str = str(request.url)
    domain_key = get_domain_key(url_str)

    cached_data = site_cache.get(domain_key)
    cache_status = "HIT" if cached_data else "MISS"

    try:
        if cached_data:
            result = await scrape(
                url_str,
                cached_selector=cached_data.get("selector"),
                cached_page_type=cached_data.get("page_type"),
                cached_field_selectors=cached_data.get("field_selectors"),
                headless=True,
            )
        else:
            result = await scrape(url_str, headless=True)
            if result.get("selector") and result.get("page_type"):
                site_cache[domain_key] = {
                    "selector": result["selector"],
                    "page_type": result["page_type"],
                    "field_selectors": result.get("field_selectors"),
                    "created_at": time.time(),
                }
                await save_cache()

        result["cache_status"] = cache_status
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Using the module string "api_server:app" allows reload to work correctly
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
