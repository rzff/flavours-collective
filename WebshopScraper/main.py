#!/usr/bin/env python3
"""
Hybrid Webshop Scraper v4
- Iterative selector discovery via Qwen 2.5 Coder
- Extracts products using BeautifulSoup
- Saves merged products.json for multiple URLs
- Stores raw HTML + metadata for debugging
"""

import os
import re
import json
import time
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

DATA_DIR = "scraper_data"
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# Local LLM: Qwen 2.5 Coder via Ollama
# ---------------------------------------------------------------------
async def local_llm_call(prompt: str, model: str = "qwen2.5-coder:14b") -> str:
    """Send a prompt to a local Ollama model (Qwen)."""
    url = "http://localhost:11434/api/generate"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json={"model": model, "prompt": prompt, "stream": False}
        ) as resp:
            data = await resp.json()
            return data.get("response", "").strip()


# ---------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------
def infer_platform(html: str, url: str) -> str:
    html_lower = html.lower()
    if "cdn.shopify.com" in html_lower or "shopify" in url:
        return "Shopify"
    elif "woocommerce" in html_lower:
        return "WooCommerce"
    elif "magento" in html_lower:
        return "Magento"
    elif "bigcommerce" in html_lower:
        return "BigCommerce"
    elif "prestashop" in html_lower:
        return "PrestaShop"
    elif "salesforce" in html_lower or "commercecloud" in html_lower:
        return "Salesforce Commerce Cloud"
    elif "squarespace" in html_lower:
        return "Squarespace"
    elif "wix" in html_lower:
        return "Wix"
    elif "webflow" in html_lower:
        return "Webflow"
    return "Custom"


# ---------------------------------------------------------------------
# BeautifulSoup extraction
# ---------------------------------------------------------------------
def extract_products_bs4(html: str, selector: str, base_url: str) -> List[Dict]:
    """Extract structured product data for a given selector."""
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select(selector)
    products = []

    for product in containers:
        try:
            name = (
                product.get("data-title")
                or product.get("title")
                or product.get_text(strip=True)
            )
            name = name.strip() if name else "N/A"

            href = product.get("href") or ""
            url = urljoin(base_url, href)

            product_id = product.get("data-product-id") or "N/A"
            color = product.get("data-color") or "N/A"
            is_new = product.get("data-newarrival") == "true"

            # Price
            price_el = product.find(["span", "div"], class_=re.compile("price|money"))
            if price_el:
                price_text = price_el.get_text(strip=True)
                price = "SOLD OUT" if "SOLD" in price_text.upper() else price_text
            else:
                price = "N/A"

            # Image
            img_tag = product.find("img", src=True)
            image_url = urljoin(base_url, img_tag["src"]) if img_tag else "N/A"

            # Badge
            badge_tag = product.find(class_=re.compile("badge|tag|label"))
            badge = badge_tag.get_text(strip=True) if badge_tag else "N/A"

            products.append(
                {
                    "name": name,
                    "url": url,
                    "price": price,
                    "product_id": product_id,
                    "color": color,
                    "is_new": is_new,
                    "badge": badge,
                    "image": image_url,
                }
            )
        except Exception as e:
            print(f"⚠️ Skipping malformed product: {e}")

    return products


# ---------------------------------------------------------------------
# Iterative selector discovery
# ---------------------------------------------------------------------
async def find_valid_selector(
    html: str, platform: str, base_url: str, max_attempts: int = 5
):
    """
    Ask Qwen iteratively for product container selectors.
    Returns (best_selector, tested_selectors, extracted_products)
    """
    tested_selectors = []
    best_selector = None
    best_products = []

    fallback_selectors = [
        "a.plp-product",
        ".product-card",
        ".product-tile",
        ".grid__item",
        ".product-item",
        ".product",
        ".item",
    ]

    for attempt in range(1, max_attempts + 1):
        context = (
            f"Previously tested selectors (0 products): {tested_selectors}"
            if tested_selectors
            else ""
        )
        prompt = f"""
You are an expert in e-commerce HTML parsing.
HTML snippet (truncated): {html[:7000]}
Platform: {platform}
{context}

Return a JSON array of up to 5 potential CSS selectors for product containers.
Do not repeat selectors already tested.
Return ONLY the JSON array.
"""
        try:
            response = await local_llm_call(prompt)
            match = re.search(r"\[.*\]", response, re.DOTALL)
            selectors = json.loads(match.group(0)) if match else []
            selectors = [
                s.strip() for s in selectors if isinstance(s, str) and s.strip()
            ]
        except Exception:
            selectors = []

        selectors = list(dict.fromkeys(selectors + fallback_selectors))  # unique
        print(f"🧩 Attempt {attempt} — trying selectors: {selectors}")

        for sel in selectors:
            if sel in tested_selectors:
                continue
            tested_selectors.append(sel)
            products = extract_products_bs4(html, sel, base_url)
            if len(products) > len(best_products):
                best_products = products
                best_selector = sel

        if best_products:
            print(f"✅ Found products with selector: {best_selector}")
            break
        else:
            print("❌ No products found this round, retrying...")

    if not best_products:
        for sel in fallback_selectors:
            products = extract_products_bs4(html, sel, base_url)
            if products:
                best_selector = sel
                best_products = products
                break

    return best_selector, tested_selectors, best_products


# ---------------------------------------------------------------------
# Unified scrape flow
# ---------------------------------------------------------------------
async def scrape(url: str, headless: bool = True) -> Dict:
    """Scrape a collection page dynamically using Qwen + BS4."""
    print(f"📡 Fetching: {url}")

    # Step 1: Download HTML
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print("⚠️ HTTP fetch failed, using browser …", e)
        browser_cfg = BrowserConfig(headless=headless)
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(
                url, config=CrawlerRunConfig(cache_mode=CacheMode.DISABLED)
            )
            html = result.html if result and result.success else ""

    if not html.strip():
        print("❌ No HTML content found.")
        return {"url": url, "products": []}

    # Step 2: Detect platform
    platform = infer_platform(html, url)
    print(f"🛒 Detected platform: {platform}")

    # Step 3: Iterative selector discovery
    best_selector, tested_selectors, best_products = await find_valid_selector(
        html, platform, url, max_attempts=5
    )
    if not best_products:
        print("😥 No products found for any selector.")
        return {"url": url, "products": []}
    print(f"✅ Best selector: {best_selector} → {len(best_products)} products")

    # Step 4: Store raw HTML + metadata
    domain = re.sub(r"[^a-zA-Z0-9]", "_", url.split("//")[-1])
    with open(f"{DATA_DIR}/{domain}_raw.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(f"{DATA_DIR}/{domain}_metadata.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "url": url,
                "platform": platform,
                "selectors_tested": tested_selectors,
                "best_selector": best_selector,
                "num_products": len(best_products),
            },
            f,
            indent=2,
        )

    return {
        "url": url,
        "platform": platform,
        "selector": best_selector,
        "products": best_products,
    }


# ---------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------
async def main():
    urls = [
        "https://www.apcstore.com/collections/all",
        # Add more URLs here
    ]
    start = time.time()

    merged_products_path = f"{DATA_DIR}/products.json"
    if os.path.exists(merged_products_path):
        with open(merged_products_path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
            # If somehow it’s a dict or string, convert to list
            if isinstance(all_data, dict):
                all_data = [all_data]
            elif isinstance(all_data, str):
                try:
                    all_data = json.loads(all_data)
                    if isinstance(all_data, dict):
                        all_data = [all_data]
                except Exception:
                    all_data = []
    else:
        all_data = []

    for url in urls:
        result = await scrape(url, headless=False)
        products = result.get("products", [])
        if products:
            # Remove old entry for same URL
            all_data = [s for s in all_data if s.get("url") != result["url"]]
            all_data.append(result)
            # Save merged data
            with open(merged_products_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {len(products)} products from {url}")
        else:
            print(f"😥 No products found for {url}")

    print(f"⏱️ Total runtime: {time.time() - start:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
