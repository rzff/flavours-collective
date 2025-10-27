#!/usr/bin/env python3
"""
Hybrid Adaptive Webshop Scraper v8 (Cache-Aware)
- `scrape` function now accepts optional cached_selector and cached_page_type
  to bypass LLM calls.
"""

import os
import re
import json
import time
import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Set

from scraper_utils import (
    infer_platform,
    extract_products_bs4,
    find_valid_selector,
)

# We only need the LLM-based detector from HtmlParser
from HtmlParser import detect_page_type
from playwright.async_api import async_playwright

DATA_DIR = "scraper_data"
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# Safe Playwright page.content fetch (unchanged)
# ---------------------------------------------------------------------
async def safe_page_content(page):
    try:
        return await page.content()
    except Exception:
        return ""


# ---------------------------------------------------------------------
# Simple Playwright fetch (unchanged)
# ---------------------------------------------------------------------
async def fetch_simple_playwright_html(url: str) -> str:
    """Just load the page and return HTML, no scrolling."""
    print("🌐 Using Playwright for initial HTML load...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            html = await safe_page_content(page)
        except Exception as e:
            print(f"⚠️ Playwright simple fetch failed: {e}")
            html = ""
        await browser.close()
    return html


# ---------------------------------------------------------------------
# Scroll function (unchanged)
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# REFACTORED: Scroll function (now more robust)
# ---------------------------------------------------------------------
async def fetch_html_with_scroll(
    url: str,
    product_selector: str,
    scroll_pause: float = 1.0,
    max_scrolls: int = 100,
    stability_checks: int = 5,
) -> str:
    """
    Launches Playwright and scrolls down, using the product_selector
    to check if new products are loading.

    NOW with more robust error handling for navigation/reloads.
    """
    print(f"🌀 Starting scroll process using selector: {product_selector}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        final_html = ""
        last_count = 0
        same_count = 0

        try:
            await page.goto(url, wait_until="domcontentloaded")
            # Get the initial HTML before any scrolling
            final_html = await safe_page_content(page)
            # Get initial count
            last_count = await page.locator(product_selector).count()
            print(f"🛒 Products loaded (initial): {last_count}")

        except Exception as e:
            error_msg = str(e).lower()
            if "context was destroyed" in error_msg or "target closed" in error_msg:
                print(f"⚠️ Page context destroyed on initial load: {e}")
            else:
                print(f"⚠️ Error during initial page load: {e}")
            await browser.close()
            return final_html  # Return whatever HTML we got (if any)

        # --- Start Scroll Loop ---
        for _ in range(max_scrolls):
            try:
                # --- 1. Use a gentler scroll method ---
                await page.keyboard.press("PageDown")
                await asyncio.sleep(scroll_pause)

                # --- 2. Check product count ---
                current_count = await page.locator(product_selector).count()
                print(f"🛒 Products loaded: {current_count}")

                # --- 3. Save the *last known good HTML* ---
                # We do this *after* a successful count
                final_html = await safe_page_content(page)

                # --- 4. Stabilization Check ---
                if current_count == last_count:
                    same_count += 1
                    if same_count >= stability_checks:
                        print(f"✅ Product count stabilized at {current_count}")
                        break
                else:
                    same_count = 0
                    last_count = current_count

            except Exception as e:
                # --- 5. Catch the context error gracefully ---
                error_msg = str(e).lower()
                if "context was destroyed" in error_msg or "target closed" in error_msg:
                    print(
                        f"⚠️ Page context destroyed during scroll (navigation?), stopping."
                    )
                else:
                    print(f"⚠️ Unknown error in scroll loop: {e}")

                # Exit the loop on ANY error
                break

        await browser.close()

        # Return the last HTML we successfully captured
        return final_html


# ---------------------------------------------------------------------
# REFACTORED: Unified scrape flow (now accepts cache)
# ---------------------------------------------------------------------
async def scrape(
    url: str,
    cached_selector: str | None = None,
    cached_page_type: str | None = None,
    headless: bool = True,
) -> Dict:
    print(f"📡 Fetching: {url}")
    start_time = time.time()

    # Step 1 & 2: Get initial HTML (static or simple Playwright)
    html = ""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        html = resp.text
        print("✅ Static HTML fetched via requests")
    except Exception as e:
        print(f"⚠️ Static fetch failed: {e}. Falling back to Playwright.")

    if not html.strip():
        html = await fetch_simple_playwright_html(url)

    if not html.strip():
        print("❌ No HTML content found after all fallbacks.")
        return {"url": url, "products": []}

    # Step 3: Detect platform (fast)
    platform = infer_platform(html, url)
    print(f"🛒 Detected platform: {platform}")

    # Step 4: Detect page type (Check cache first)
    page_type = ""
    if cached_page_type:
        page_type = cached_page_type
        print(f"⚡ Cache HIT for Page Type: {page_type}")
    else:
        print("🐌 LLM call for Page Type...")
        page_type = await detect_page_type(html, url)  # Slow LLM call
        print(f"🔒 LLM detected Page Type: {page_type}")

    # Step 5: Iterative selector discovery (Check cache first)
    best_selector = None
    tested_selectors = []
    products = []

    if cached_selector:
        print(f"⚡ Cache HIT for Selector: {cached_selector}")
        best_selector = cached_selector
        tested_selectors = [cached_selector]
        products = extract_products_bs4(html, best_selector, url)
    else:
        print("🐌 LLM call for Selector...")
        best_selector, tested_selectors, products = await find_valid_selector(
            html, platform, url
        )

    if not products or not best_selector:
        print("😥 No products found on initial page load.")
        return {
            "url": url,
            "platform": platform,
            "page_type": page_type,  # Return page_type even if selector fails
            "selector": None,
            "products": [],
        }
    print(f"✅ Initial selector: {best_selector} → {len(products)} products")

    # Step 6: If dynamic, scroll for all products
    final_html = html
    if page_type in ("infinite_scroll", "pagination"):
        print(f"🌐 Page type is {page_type}, scrolling for all products...")
        final_html = await fetch_html_with_scroll(url, best_selector)
    else:
        print("✅ Page type is static, no scrolling needed.")

    # Step 7: Final extraction from fully-loaded HTML
    final_products = extract_products_bs4(final_html, best_selector, url)
    print(f"🏁 Final extraction: {len(final_products)} products found.")

    # Step 8: Store raw HTML + metadata
    domain = re.sub(r"[^a-zA-Z0-9]", "_", url.split("//")[-1])
    with open(f"{DATA_DIR}/{domain}_raw.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    with open(f"{DATA_DIR}/{domain}_metadata.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "url": url,
                "platform": platform,
                "page_type": page_type,
                "selectors_tested": tested_selectors,
                "best_selector": best_selector,
                "num_products": len(final_products),
                "scrape_time_s": time.time() - start_time,
                "was_cached": bool(cached_selector),
            },
            f,
            indent=2,
        )

    # Return the dictionary for the API
    return {
        "url": url,
        "platform": platform,
        "page_type": page_type,
        "selector": best_selector,
        "products": final_products,
    }


# ---------------------------------------------------------------------
# CLI Entrypoint (Unchanged, but will always be a "Cache Miss")
# ---------------------------------------------------------------------
async def main():
    urls = [
        "https://eu.aimeleondore.com/collections/shop-all",
        "https://ninetyfour.world/collections/t-shirts",
    ]
    start = time.time()

    # ... (rest of main function is unchanged)
    # Note: Running this directly will NOT use the API's cache.
    # It will always run the "cache miss" logic.

    merged_products_path = f"{DATA_DIR}/products.json"
    if os.path.exists(merged_products_path):
        with open(merged_products_path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
            if isinstance(all_data, dict):
                all_data = [all_data]
            elif isinstance(all_data, str):
                try:
                    all_data = json.loads(all_data)
                except Exception:
                    all_data = []
            if isinstance(all_data, dict):
                all_data = [all_data]
    else:
        all_data = []

    for url in urls:
        # This call will always be a "cache miss"
        result = await scrape(url, headless=True)
        products = result.get("products", [])
        if products:
            all_data = [s for s in all_data if s.get("url") != result["url"]]
            all_data.append(result)
            with open(merged_products_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {len(products)} products from {url}")
        else:
            print(f"😥 No products found for {url}")

    print(f"⏱️ Total runtime: {time.time() - start:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
