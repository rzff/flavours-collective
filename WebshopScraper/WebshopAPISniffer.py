#!/usr/bin/env python3
"""
Webshop API Sniffer
- Detects product API endpoints from SPA / dynamic storefronts
- Fetches all products in JSON format
"""

import asyncio
import json
import re
import aiohttp
from typing import List, Dict
from playwright.async_api import async_playwright


async def sniff_api_endpoints(url: str) -> List[str]:
    """Launches the page and inspects XHR / Fetch calls to find JSON endpoints"""
    endpoints = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def log_request(request):
            if request.resource_type in ["xhr", "fetch"]:
                if "product" in request.url.lower():
                    endpoints.add(request.url)

        page.on("request", log_request)
        await page.goto(url, wait_until="networkidle")
        # Wait a few seconds for dynamic requests
        await asyncio.sleep(5)
        await browser.close()

    return list(endpoints)


async def fetch_products_from_api(api_url: str) -> List[Dict]:
    """Fetch product JSON from a detected API endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                api_url, headers={"User-Agent": "Mozilla/5.0"}
            ) as resp:
                data = await resp.json()
                # Attempt to detect products list in JSON
                if isinstance(data, dict):
                    for key in data:
                        if isinstance(data[key], list) and all(
                            "id" in p for p in data[key]
                        ):
                            return data[key]
                elif isinstance(data, list):
                    return data
        except Exception as e:
            print(f"⚠️ Failed to fetch {api_url}: {e}")
    return []


async def main(url: str):
    endpoints = await sniff_api_endpoints(url)
    print(f"🔎 Detected API endpoints: {endpoints}")

    for ep in endpoints:
        products = await fetch_products_from_api(ep)
        if products:
            print(f"✅ Fetched {len(products)} products from {ep}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python WebshopAPISniffer.py <URL>")
    else:
        url = sys.argv[1]
        asyncio.run(main(url))
