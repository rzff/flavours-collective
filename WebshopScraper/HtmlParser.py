#!/usr/bin/env python3
"""
Adaptive HTML Retriever Microservice with API fallback
- Detects page type (pagination / infinite_scroll / static)
- Dynamically detects product & load-more selectors
- Fetches total product count (Qwen + heuristics)
- Fully scrolls or paginates until all products are loaded
- Falls back to API sniffing for incomplete dynamic pages
"""

import asyncio
import json
import re
from typing import List, Set, Dict
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper_utils import local_llm_call
from WebshopAPISniffer import sniff_api_endpoints, fetch_products_from_api


# ---------------------------
# Page type detection
# ---------------------------
async def detect_page_type(html: str, url: str) -> str:
    prompt = f"""
You are an expert in e-commerce HTML analysis.
HTML snippet (truncated): {html[:7000]}
URL: {url}
Classify the page as one of: "pagination", "infinite_scroll", "static".
Return ONLY the page type string.
"""
    try:
        response = await local_llm_call(prompt)
        response = response.strip().lower()
        if "pagination" in response:
            page_type = "pagination"
        elif "scroll" in response:
            page_type = "infinite_scroll"
        else:
            page_type = "static"
    except Exception:
        page_type = "static"

    # Heuristic override
    product_like_count = len(
        re.findall(r'class=["\'].*product.*["\']', html, re.IGNORECASE)
    )
    has_load_more = bool(re.search(r"button.*(load|more|show)", html, re.IGNORECASE))
    if page_type == "static" and (product_like_count > 20 or has_load_more):
        page_type = "infinite_scroll"

    print(f"🔎 Detected page type: {page_type} (Qwen + heuristic)")
    return page_type


# ---------------------------
# Product container detection
# ---------------------------
async def detect_product_selector(html: str, platform: str, url: str) -> str:
    prompt = f"""
You are an expert in e-commerce HTML parsing and CSS selector analysis.

CONTEXT:
- URL: {url}
- Platform: {platform}
- Goal: Find the BEST CSS selector for individual product containers

CRITERIA for good product selectors:
1. Should target INDIVIDUAL product containers, not product lists/wrappers
2. Should be specific enough to avoid including navigation, headers, footers
3. Should match multiple products on the page
4. Should contain product-specific elements (images, prices, names)
5. Prefer class-based selectors over tag-based ones
6. Avoid overly generic selectors like "div" or "li" without classes

COMMON PATTERNS by platform:
- Shopify: .product-item, .grid-item, .product-card, [data-product-handle]
- WooCommerce: .product, .woocommerce-product, .type-product
- Custom: Look for repeating patterns with product images, prices, "add to cart"

BAD SELECTORS to avoid:
- Selectors that include prices/names inside them (should be separate)
- Selectors that match only one product
- Selectors that include non-product content

HTML snippet (first 8000 chars):
{html[:8000]}

ANALYSIS TASK:
1. Identify all potential product container selectors
2. Rank them by specificity and accuracy
3. Choose the best one that isolates individual products

Return ONLY a JSON array of the top 3 CSS selectors, most specific first.
Example: ["[data-product-id]", ".product-card", ".grid-item"]
"""
    try:
        response = await local_llm_call(prompt)
        print(f"🔍 LLM Product Selector Response: {response}")

        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            selectors = json.loads(match.group(0))
            selectors = [s.strip() for s in selectors if s.strip()]

            # Validate selectors aren't too generic
            good_selectors = []
            for selector in selectors:
                if (
                    len(selector) > 3
                    and not selector.lower() in ["div", "li", "a", "article", "section"]
                    and not selector.startswith("body")
                    and not selector.startswith("html")
                ):
                    good_selectors.append(selector)

            if good_selectors:
                print(f"✅ Selected product selector: {good_selectors[0]}")
                return good_selectors[0]

        # Fallback with platform-specific defaults
        fallbacks = {
            "shopify": ".product-item",
            "woocommerce": ".product",
            "custom": '[class*="product"], [class*="item"]',
        }
        return fallbacks.get(platform.lower(), ".product-item")

    except Exception as e:
        print(f"❌ Product selector detection failed: {e}")
        return ".product-item"


async def detect_load_more_selectors(html: str, platform: str) -> List[str]:
    prompt = f"""
You are an expert in e-commerce HTML parsing.
HTML snippet (truncated): {html[:15000]}
Platform: {platform}
Return a JSON array of CSS selectors for buttons that load more products.
Only return the array.
"""
    try:
        response = await local_llm_call(prompt)
        match = re.search(r"\[.*\]", response, re.DOTALL)
        selectors = json.loads(match.group(0)) if match else []
        return [s.strip() for s in selectors if s.strip()]
    except Exception:
        return []


# ---------------------------
# Total product detection
# ---------------------------
def extract_total_from_html(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(
        class_=re.compile(r"(count|total|results|items)", re.IGNORECASE)
    )
    for c in candidates:
        text = c.get_text(strip=True).replace(",", "")
        match = re.search(r"\d+", text)
        if match:
            return int(match.group(0))
    return 0


async def detect_total_products(html: str, url: str, max_attempts: int = 2) -> int:
    for attempt in range(max_attempts):
        prompt = f"""
You are an expert in e-commerce HTML parsing.
HTML snippet (truncated): {html[:7000]}
URL: {url}
Return the total number of products listed on this page.
If no total is visible, return 0.
Return ONLY the number.
"""
        try:
            response = await local_llm_call(prompt)
            match = re.search(r"\d+", response)
            if match:
                total = int(match.group())
                if total > 0:
                    return total
        except Exception:
            pass
        html = html[:5000]

    total = extract_total_from_html(html)
    if total > 0:
        return total

    patterns = [
        r"of\s+(\d+)\s+products",
        r"(\d+)\s+results",
        r"totalProducts\":\s*(\d+)",
    ]
    for pat in patterns:
        match = re.search(pat, html, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return 0


# ---------------------------
# API fallback
# ---------------------------
async def fetch_products_via_api(url: str) -> List[Dict]:
    endpoints = await sniff_api_endpoints(url)
    print(f"🔎 Detected API endpoints: {endpoints}")

    best_products = []
    best_endpoint = None

    for ep in endpoints:
        products = await fetch_products_from_api(ep)
        if len(products) > len(best_products):
            best_products = products
            best_endpoint = ep

    if best_products:
        print(f"✅ Retrieved {len(best_products)} products via API: {best_endpoint}")
    else:
        print("⚠️ No products retrieved via API.")

    return best_products


# ---------------------------
# Fetch page HTML with adaptive scroll + API fallback
# ---------------------------
# ---------------------------
# Fetch page HTML with adaptive scroll
# ---------------------------
async def fetch_page_html(
    url: str,
    scroll_pause: float = 1.5,
    max_scrolls: int = 200,
    stability_checks: int = 5,
) -> str:
    import requests
    from playwright.async_api import async_playwright

    # Step 0: Try static HTML first
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
        html = resp.text
        print("✅ Static HTML fetched via requests")
    except Exception:
        html = ""
        print("⚠️ Static fetch failed, falling back to Playwright")

    # Step 1: Detect page type from static HTML
    page_type = await detect_page_type(html, url) if html else "infinite_scroll"
    platform = "Custom"

    # Step 2: Detect selectors heuristically
    product_selector = (
        await detect_product_selector(html, platform, url) if html else ".product-item"
    )
    load_more_selectors = (
        await detect_load_more_selectors(html, platform) if html else []
    )

    # Step 3: Total product estimate
    total_products = await detect_total_products(html, url) if html else 0

    # Step 4: Playwright fallback for dynamic pages or infinite scroll
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            print("⚠️ Initial page.goto timeout, continuing anyway")

        seen_urls: Set[str] = set()
        last_count = 0
        same_count = 0

        if page_type == "infinite_scroll":
            for scroll_idx in range(max_scrolls):
                try:
                    # Scroll down
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(scroll_pause)

                    # Click load-more buttons safely
                    for sel in load_more_selectors:
                        try:
                            buttons = page.locator(sel)
                            for j in range(await buttons.count()):
                                await buttons.nth(j).click()
                                await asyncio.sleep(scroll_pause)
                        except Exception:
                            continue

                    # Refresh product list after potential DOM replacement
                    product_elements = page.locator(product_selector)
                    for j in range(await product_elements.count()):
                        try:
                            href = await product_elements.nth(j).get_attribute("href")
                            if href:
                                seen_urls.add(href)
                        except Exception:
                            continue

                    current_count = len(seen_urls)
                    print(f"🛒 Products loaded: {current_count}")

                    # Stop if total reached
                    if total_products and current_count >= total_products:
                        print(f"✅ Reached total product count: {total_products}")
                        break

                    # Stabilization check
                    if current_count == last_count:
                        same_count += 1
                        if same_count >= stability_checks:
                            print(f"✅ Product count stabilized at {current_count}")
                            break
                    else:
                        same_count = 0
                        last_count = current_count

                except Exception as e:
                    print(f"⚠️ Scroll loop caught exception, retrying: {e}")
                    await asyncio.sleep(scroll_pause)

        # Fetch final HTML
        try:
            html = await page.content()
        except Exception as e:
            print(f"⚠️ Could not get final page content: {e}")

        await browser.close()

    return html
