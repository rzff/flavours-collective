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


# Add to scraper_utils.py


async def detect_field_selectors(
    html: str, platform: str, product_selector: str
) -> Dict[str, List[str]]:
    """
    Ask LLM to detect optimal CSS selectors for each product field.
    """
    print("🤖 Starting LLM field selector detection...")

    # Use a smaller HTML sample but include actual product examples
    soup = BeautifulSoup(html, "html.parser")
    sample_containers = soup.select(product_selector)

    if sample_containers:
        # Use actual product HTML for better detection
        sample_html = ""
        for i, container in enumerate(sample_containers[:3]):  # Use first 3 products
            sample_html += f"\n--- Product {i + 1} ---\n"
            sample_html += str(container.prettify())[:1000]  # Limit size
    else:
        sample_html = html[:3000]

    prompt = f"""
You are an expert in e-commerce HTML parsing analyzing product containers.

Platform: {platform}
Product container selector: {product_selector}

Sample product containers:
{sample_html}

Analyze these product containers and return a JSON object with CSS selectors for each field.
Return the most specific selectors first, then fallbacks.

IMPORTANT: The selectors should work FROM WITHIN the product container (e.g., ".product-card .product-name" not just ".product-name")

Return format:
{{
    "name": ["selector1", "selector2"],
    "price": ["selector1", "selector2"],
    "image": ["selector1", "selector2"],
    "description": ["selector1", "selector2"],
    "url": ["selector1", "selector2"]
}}

Focus on:
- Name: Look for headings (h1-h4), elements with class containing: title, name, product-name
- Price: Look for elements with class containing: price, cost, money, currency
- Image: Look for img tags with class containing: image, img, product-image
- Description: Look for p tags with class containing: desc, description, product-desc
- URL: Look for a tags with class containing: link, product-link, or href attributes

Return ONLY the JSON object.
"""

    try:
        print("📤 Sending request to LLM...")
        response = await local_llm_call(prompt)
        print(f"📥 LLM raw response: {response}")

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            selectors = json.loads(match.group(0))
            print(f"✅ LLM returned field selectors: {selectors}")

            # Validate and ensure selectors are relative to container
            expected_fields = ["name", "price", "image", "description", "url"]
            validated_selectors = {}

            for field in expected_fields:
                field_sel = selectors.get(field, [])
                # Ensure selectors are properly formatted
                if not field_sel:
                    field_sel = []
                elif isinstance(field_sel, str):
                    field_sel = [field_sel]

                validated_selectors[field] = field_sel

            return validated_selectors
        else:
            print("❌ No JSON found in LLM response")
    except Exception as e:
        print(f"❌ LLM field selector detection failed: {e}")

    # Better fallback selectors that are relative to container
    fallback = {
        "name": [
            "h1",
            "h2",
            "h3",
            "h4",
            ".title",
            "[class*='title']",
            "[class*='name']",
        ],
        "price": [
            ".price",
            "[class*='price']",
            ".money",
            "[class*='cost']",
            "[class*='currency']",
        ],
        "image": ["img", "[class*='image']", "[class*='img']", ".product-image"],
        "description": ["p", ".description", "[class*='desc']", ".product-desc"],
        "url": ["a", "[href]", ".product-link", "[class*='link']"],
    }
    print(f"🔄 Using fallback selectors: {fallback}")
    return fallback


def extract_field_value(
    element, selectors: List[str], field_type: str = "text", base_url: str = ""
) -> str:
    """
    Extract field value using prioritized selectors.
    """
    soup = (
        element
        if isinstance(element, BeautifulSoup)
        else BeautifulSoup(str(element), "html.parser")
    )

    # Special case: if the element itself is a link and we're looking for URL
    if field_type == "url" and soup.name == "a":
        href = soup.get("href")
        if href:
            full_url = urljoin(base_url, href)
            print(f"   🔗 Found URL from container href: {full_url}")
            return full_url

    # Special case: if the element itself is an image and we're looking for image URL
    if field_type == "image" and soup.name == "img":
        src = soup.get("src") or soup.get("data-src") or soup.get("data-lazy-src")
        if src:
            full_url = urljoin(base_url, src)
            print(f"   🖼️ Found image from container src: {full_url}")
            return full_url

    for selector in selectors:
        try:
            found = soup.select_one(selector)
            if found:
                if field_type == "text":
                    text = found.get_text(strip=True)
                    if text and text not in ["", "null", "undefined"]:
                        print(
                            f"   ✅ Found text with selector '{selector}': '{text[:50]}...'"
                        )
                        return text
                    else:
                        print(f"   ⚠️ Selector '{selector}' found but text empty")

                elif field_type == "url":
                    href = found.get("href")
                    if href:
                        full_url = urljoin(base_url, href)
                        print(f"   ✅ Found URL with selector '{selector}': {full_url}")
                        return full_url
                    else:
                        print(f"   ⚠️ Selector '{selector}' found but no href attribute")

                elif field_type == "image":
                    src = (
                        found.get("src")
                        or found.get("data-src")
                        or found.get("data-lazy-src")
                    )
                    if src:
                        full_url = urljoin(base_url, src)
                        print(
                            f"   ✅ Found image with selector '{selector}': {full_url}"
                        )
                        return full_url
                    else:
                        print(f"   ⚠️ Selector '{selector}' found but no src attribute")

                elif field_type == "price":
                    text = found.get_text(strip=True)
                    # Clean price text - look for currency symbols and numbers
                    price_match = re.search(r"[\$£€]?[\d,]+\.?\d*", text)
                    if price_match:
                        price = price_match.group(0)
                        print(
                            f"   ✅ Found price with selector '{selector}': '{price}'"
                        )
                        return price
                    else:
                        print(
                            f"   ⚠️ Selector '{selector}' found but no price pattern in: '{text}'"
                        )

            else:
                print(f"   ❌ Selector '{selector}' not found")

        except Exception as e:
            print(f"   ⚠️ Error with selector '{selector}': {e}")
            continue

    # Final fallbacks for URL field
    if field_type == "url":
        # Try to find any link within the container
        any_link = soup.find("a")
        if any_link and any_link.get("href"):
            full_url = urljoin(base_url, any_link.get("href"))
            print(f"   🔗 Fallback URL found: {full_url}")
            return full_url

        # If container has href itself (should be caught by special case above, but just in case)
        if soup.get("href"):
            full_url = urljoin(base_url, soup.get("href"))
            print(f"   🔗 Fallback URL from container: {full_url}")
            return full_url

    # Final fallback for image field
    if field_type == "image":
        # Try to find any image within the container
        any_image = soup.find("img")
        if any_image:
            src = (
                any_image.get("src")
                or any_image.get("data-src")
                or any_image.get("data-lazy-src")
            )
            if src:
                full_url = urljoin(base_url, src)
                print(f"   🖼️ Fallback image found: {full_url}")
                return full_url

    print(f"   ❌ No {field_type} found with any selector")
    return ""


def extract_price_specialized(element) -> str:
    """
    Specialized price extraction with multiple strategies.
    """
    soup = (
        element
        if isinstance(element, BeautifulSoup)
        else BeautifulSoup(str(element), "html.parser")
    )

    # Strategy 1: Look for common price patterns
    price_patterns = [
        r"\$\d+\.?\d*",
        r"€\d+\.?\d*",
        r"£\d+\.?\d*",
        r"\d+\.?\d*\s*(USD|EUR|GBP)",
    ]

    text_content = soup.get_text()
    for pattern in price_patterns:
        match = re.search(pattern, text_content)
        if match:
            return match.group(0)

    # Strategy 2: Look for data attributes
    price_attrs = ["data-price", "data-product-price", "data-item-price"]
    for attr in price_attrs:
        price = soup.find(attrs={attr: True})
        if price:
            return price[attr]

    return ""


def check_availability(element) -> bool:
    """
    Check if product is in stock.
    """
    soup = (
        element
        if isinstance(element, BeautifulSoup)
        else BeautifulSoup(str(element), "html.parser")
    )

    # Look for out-of-stock indicators
    out_of_stock_indicators = [
        ".out-of-stock",
        ".sold-out",
        '[class*="out"]',
        '[class*="sold"]',
        ".unavailable",
        ".stock-out",
    ]

    for selector in out_of_stock_indicators:
        if soup.select_one(selector):
            return False

    # Look for in-stock indicators
    in_stock_indicators = [
        ".in-stock",
        ".available",
        '[class*="in-stock"]',
        ".add-to-cart",
    ]

    for selector in in_stock_indicators:
        if soup.select_one(selector):
            return True

    # Default to available if no clear indicators
    return True


async def extract_products_bs4_enhanced(
    html: str,
    selector: str,
    base_url: str,
    platform: str = "Custom",
    field_selectors: Dict[str, List[str]] | None = None,
) -> List[Dict]:
    """
    Enhanced product extraction with LLM-detected field selectors.
    """
    print(f"🔍 Starting enhanced extraction with selector: {selector}")
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select(selector)
    print(f"📦 Found {len(containers)} product containers")

    if not containers:
        print("❌ No containers found with selector:", selector)
        return []

    # Get field selectors from LLM (once per page)
    if not field_selectors:
        print("🤖 Detecting field selectors with LLM...")
        field_selectors = await detect_field_selectors(html, platform, selector)
    else:
        print("⚡ Using cached field selectors")

    print(f"🎯 Field selectors: {field_selectors}")

    # Debug: Show actual HTML structure of first container
    if containers:
        first_container = containers[0]
        print(f"🔎 First container HTML structure:")
        print(f"   Text preview: {first_container.get_text(strip=True)[:100]}...")
        print(f"   Classes: {first_container.get('class', [])}")
        print(f"   Tag: {first_container.name}")

        # Test each field selector on the first container
        print(f"🧪 Testing field selectors on first container:")
        for field, selectors in field_selectors.items():
            for sel in selectors[:2]:  # Test first 2 selectors
                try:
                    found = first_container.select_one(sel)
                    if found:
                        if field == "image":
                            src = found.get("src") or found.get("data-src")
                            print(f"   ✅ {field} selector '{sel}': FOUND (src: {src})")
                        else:
                            text = found.get_text(strip=True)
                            print(
                                f"   ✅ {field} selector '{sel}': FOUND ('{text[:50]}...')"
                            )
                    else:
                        print(f"   ❌ {field} selector '{sel}': NOT FOUND")
                except Exception as e:
                    print(f"   ⚠️ {field} selector '{sel}': ERROR - {e}")

    products = []
    successful_extractions = 0

    for i, product in enumerate(containers):
        try:
            # Extract each field using prioritized selectors
            name = extract_field_value(
                product, field_selectors["name"], "text", base_url
            )
            price = extract_field_value(
                product, field_selectors["price"], "price", base_url
            )
            image_url = extract_field_value(
                product, field_selectors["image"], "image", base_url
            )
            description = extract_field_value(
                product, field_selectors["description"], "text", base_url
            )
            product_url = extract_field_value(
                product, field_selectors["url"], "url", base_url
            )

            # Fallback for price if standard extraction fails
            if not price:
                price = extract_price_specialized(product)

            # Ensure we have at least a name to consider it a valid product
            if name and name != "N/A" and name.strip():
                products.append(
                    {
                        "name": name,
                        "url": product_url,
                        "price": price,
                        "image_url": image_url,
                        "description": description,
                        "in_stock": check_availability(product),
                    }
                )
                successful_extractions += 1
            else:
                # Debug why product was skipped
                if i == 0:  # Only debug first product to avoid spam
                    print(f"   ❌ Skipping product - name: '{name}'")

        except Exception as e:
            if i == 0:  # Only debug first error
                print(f"⚠️ Error processing product: {e}")
            continue

    print(
        f"🏁 Extraction complete: {successful_extractions}/{len(containers)} products successfully extracted"
    )

    # If enhanced extraction failed completely, fall back to basic extraction
    if successful_extractions == 0:
        print("🔄 Enhanced extraction failed, falling back to basic extraction...")
        from scraper_utils import extract_products_bs4

        basic_products = extract_products_bs4(html, selector, base_url)
        print(f"📦 Basic extraction found: {len(basic_products)} products")
        return basic_products

    return products
