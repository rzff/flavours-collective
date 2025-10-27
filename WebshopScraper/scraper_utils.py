#!/usr/bin/env python3
"""
Shared utilities for Hybrid Webshop Scraper
- Platform detection
- LLM calls (Qwen via Ollama)
- Product extraction (BeautifulSoup)
- Iterative CSS selector discovery
"""

import json
import re
from typing import List, Tuple, Dict
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import aiohttp


# ---------------------------------------------------------------------
# Local LLM (unchanged)
# ---------------------------------------------------------------------
async def local_llm_call(prompt: str, model: str = "qwen2.5-coder:14b") -> str:
    # ... (content unchanged)
    url = "http://localhost:11434/api/generate"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json={"model": model, "prompt": prompt, "stream": False}
        ) as resp:
            data = await resp.json()
            return data.get("response", "").strip()


# ---------------------------------------------------------------------
# Platform detection (unchanged)
# ---------------------------------------------------------------------
def infer_platform(html: str, url: str) -> str:
    # ... (content unchanged)
    html_lower = html.lower()
    if "cdn.shopify.com" in html_lower or "shopify" in url:
        return "Shopify"
    elif "woocommerce" in html_lower:
        return "WooCommerce"
    # ... (rest is unchanged)
    return "Custom"


# ---------------------------------------------------------------------
# BeautifulSoup product extraction (unchanged)
# ---------------------------------------------------------------------
def extract_products_bs4(html: str, selector: str, base_url: str) -> List[Dict]:
    # ... (content unchanged)
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select(selector)
    products = []
    # ... (rest is unchanged)
    for product in containers:
        try:
            name = (
                product.get("data-title")
                or product.get("title")
                or product.get_text(strip=True)
            )
            name = name.strip() if name else "N/A"
            # ... (all extraction logic unchanged)
            href = product.get("href") or ""
            url = urljoin(base_url, href)
            # ...
            products.append(
                {
                    "name": name,
                    "url": url,
                    # ...
                }
            )
        except Exception as e:
            print(f"⚠️ Skipping malformed product: {e}")

    return products


# ---------------------------------------------------------------------
# Iterative CSS selector discovery (SIMPLIFIED)
# ---------------------------------------------------------------------
async def find_valid_selector(
    html: str, platform: str, base_url: str, max_attempts: int = 5
) -> Tuple[str, List[str], List[Dict]]:
    """
    Iteratively ask Qwen for product container selectors.
    (Removed 'mode' parameter, always uses LLM + fallbacks)
    Returns: (best_selector, tested_selectors, extracted_products)
    """
    tested_selectors = []
    best_selector = None
    best_products = []

    fallback_selectors = [
        "a.product-item",
        ".product-card",
        ".product-tile",
        ".product-grid__item",
        ".grid__item",
        ".product-item",
        ".product",
        ".item",
        "li.product",
        "a.plp-product",
    ]

    print("🔒 Using LLM for selector discovery...")
    for attempt in range(1, max_attempts + 1):
        context = (
            f"Previously tested selectors: {tested_selectors}"
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
            selectors = [s.strip() for s in selectors if s.strip()]
        except Exception:
            selectors = []

        # Unique, LLM selectors first, then fallbacks
        selectors = list(dict.fromkeys(selectors + fallback_selectors))
        print(f"🧩 Attempt {attempt} — trying {len(selectors)} selectors...")

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
            break  # Found a working selector

    return best_selector, tested_selectors, best_products
