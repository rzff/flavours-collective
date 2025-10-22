#!/usr/bin/env python3
"""
Hybrid Webshop Scraper v3
Qwen2.5-Coder proposes multiple product selectors → test each with BeautifulSoup.
Stores raw HTML, all tested selectors, successful one, and detected e-commerce platform.
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
from typing import List, Dict, Optional
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
# E-commerce platform detection
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
# Ask Qwen for product selectors (plural)
# ---------------------------------------------------------------------
async def find_product_selectors(html: str, platform: str) -> List[str]:
    """
    Ask Qwen for a JSON list of potential CSS selectors for product containers.
    Returns list like ["a.plp-product", ".product-card", ".grid__item"].
    """
    prompt = f"""
You are an expert in HTML structure analysis for e-commerce.
The following HTML is from a {platform} store.

Identify multiple possible CSS selectors that likely correspond
to individual product containers in a product listing page.

Rules:
- Return **only JSON array** like:
  ["a.plp-product", ".product-card", ".grid__item"]
- Do not include explanations or text outside JSON.

HTML (truncated):
{html[:8000]}
"""
    try:
        response = await local_llm_call(prompt)
        # Attempt to parse a JSON array from response
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if not match:
            return []
        arr = json.loads(match.group(0))
        # Keep only strings and remove duplicates
        return list({s.strip() for s in arr if isinstance(s, str) and s.strip()})
    except Exception as e:
        print("⚠️ Selector identification failed:", e)
        return []


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
# Unified scrape flow
# ---------------------------------------------------------------------
async def scrape(url: str, headless: bool = True) -> Dict:
    """Scrape a collection page dynamically using Qwen + BS4."""
    print(f"📡 Fetching: {url}")

    # --- Step 1: Download HTML ---
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

    # --- Step 2: Detect platform ---
    platform = infer_platform(html, url)
    print(f"🛒 Detected platform: {platform}")

    # --- Step 3: Ask Qwen for selectors ---
    print("🔍 Asking Qwen for product selectors …")
    selectors = await find_product_selectors(html, platform)

    # --- Step 4: Fallback selectors if LLM fails ---
    fallback_selectors = [
        "a.plp-product",
        ".product-card",
        ".product-tile",
        ".grid__item",
        ".product-item",
        ".product",
        ".item",
        ".collection-product",
    ]
    selectors = selectors or fallback_selectors

    print(f"🧩 Testing {len(selectors)} potential selectors …")

    # --- Step 5: Try each selector until one works well ---
    best_selector = None
    best_products = []

    for sel in selectors:
        products = extract_products_bs4(html, sel, url)
        if len(products) >= len(best_products):
            best_products = products
            best_selector = sel

    if not best_products:
        print("😥 No products found for any selector.")
        return {"url": url, "products": []}

    print(f"✅ Best selector: {best_selector} → {len(best_products)} products")

    # --- Step 6: Store raw HTML + metadata ---
    domain = re.sub(r"[^a-zA-Z0-9]", "_", url.split("//")[-1])
    with open(f"{DATA_DIR}/{domain}_raw.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(f"{DATA_DIR}/{domain}_metadata.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "url": url,
                "platform": platform,
                "selectors_tested": selectors,
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
    url = "https://www.aimeleondore.com/collections/shop-all"
    start = time.time()

    result = await scrape(url, headless=False)
    elapsed = time.time() - start

    products = result.get("products", [])
    if products:
        out_path = f"{DATA_DIR}/products.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Extracted {len(products)} products from {result['platform']}")
        print(f"💾 Saved structured data to {out_path}")
        print(f"💾 Raw HTML + metadata saved in {DATA_DIR}/")

        # Markdown preview
        headers = products[0].keys()
        table = "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join([":---" for _ in headers]) + " |\n"
        for p in products[:10]:
            table += "| " + " | ".join(str(p.get(h, "")) for h in headers) + " |\n"
        print("\n🪄 Markdown Preview (top 10):\n")
        print(table)
    else:
        print("😥 Nothing found.")

    print(f"⏱️ Runtime: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
