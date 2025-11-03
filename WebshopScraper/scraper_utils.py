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
import logging
from typing import List, Tuple, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import aiohttp

MAX_SELECTORS_TO_TEST = 50
MIN_PRODUCTS_REQUIRED = 2
SAMPLE_SIZE = 3

SCORE_WEIGHTS = {
    "has_name": 30,
    "has_price": 30,
    "has_image": 20,
    "has_url": 10,
    "is_likely_product": 10,
}

PLATFORM_PATTERNS = {
    "Shopify": [
        "[data-product-handle]",
        "[data-product-id]",
        "[data-product]",
        ".product-card",
        ".product-item",
    ],
    "WooCommerce": [
        ".type-product",
        "[data-id]",
        "[data-item]",
        ".woocommerce-loop-product",
    ],
    "Custom": [
        '[class*="product"]',
        '[class*="item"]',
        '[class*="card"]',
        '[class*="grid"]',
        '[class*="list"]',
    ],
}

NAVIGATION_INDICATORS = [
    "home",
    "shop",
    "collection",
    "category",
    "sale",
    "clearance",
    "new arrivals",
    "men",
    "women",
    "kids",
    "accessories",
    "view all",
    "see all",
    "browse all",
    "account",
    "cart",
    "checkout",
    "login",
    "about",
    "contact",
    "help",
    "faq",
]

FIELD_EXTRACTION_PRIORITIES = {
    "name": [
        "h1",
        "h2",
        "h3",
        "h4",
        ".title",
        "[class*='title']",
        "[class*='name']",
        "[class*='product']",
        "[data-product-title]",
        "[data-title]",
        ".product-title",
        ".item-title",
        "a[class*='title']",
        "a[class*='name']",
        ".card-title",
        ".grid-title",
    ],
    "price": [
        ".price",
        "[class*='price']",
        ".money",
        "[class*='cost']",
        "[class*='currency']",
        "[data-price]",
        "[data-product-price]",
        ".product-price",
        ".item-price",
        ".current-price",
        ".sale-price",
        ".regular-price",
    ],
    "image": [
        "img",
        "[class*='image']",
        "[class*='img']",
        ".product-image",
        ".item-image",
        "[data-src]",
        "[data-lazy-src]",
        ".card-image",
        ".grid-image",
        "a img",
        ".product-card img",
        ".item-card img",
    ],
    "url": [
        "a[href*='/products/']",
        "a[href*='/product/']",
        "a[class*='product']",
        "a[class*='item']",
        "a[href*='item']",
        "[data-product-url]",
        "[data-href]",
        "a.card",
        "a.grid-item",
        "a[class*='link']",
        "a.title",
        "a.name",
    ],
    "description": [
        "p",
        ".description",
        "[class*='desc']",
        ".product-desc",
        ".item-desc",
        ".excerpt",
        ".summary",
        "[class*='text']",
        ".card-text",
    ],
}
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)

_soup_cache = {}


def ensure_serializable_products(products: List[Dict]) -> List[Dict]:
    """Ensure all product data is JSON serializable"""
    serializable_products = []
    for product in products:
        serializable_product = {}
        for key, value in product.items():
            if value is None:
                serializable_product[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                serializable_product[key] = value
            else:
                serializable_product[key] = str(value)
        serializable_products.append(serializable_product)
    return serializable_products


def get_cached_soup(html: str) -> BeautifulSoup:
    cache_key = hash(html)
    if cache_key not in _soup_cache:
        _soup_cache[cache_key] = BeautifulSoup(html, "html.parser")
    return _soup_cache[cache_key]


def is_navigation_text(text: str) -> bool:
    if not text or len(text.strip()) < 2:
        return True

    text_lower = text.lower().strip()

    if text_lower in NAVIGATION_INDICATORS:
        return True

    for indicator in NAVIGATION_INDICATORS:
        if (
            f" {indicator} " in f" {text_lower} "
            or text_lower.startswith(f"{indicator} ")
            or text_lower.endswith(f" {indicator}")
            or text_lower == indicator
        ):
            return True

    if len(text_lower) < 3:
        return True

    if text.isupper() and len(text) < 25:
        return True

    filter_patterns = [
        r"^\d+-\d+$",
        r"^\$\d+$",
        r"^color:",
        r"^size:",
    ]

    for pattern in filter_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def is_valid_product_url(href: str, base_url: str) -> bool:
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return False

    href_lower = href.lower()
    base_domain = urlparse(base_url).netloc.lower()

    if href_lower == base_url.lower():
        return False

    non_product_patterns = [
        "/collections/",
        "/search",
        "/account",
        "/cart",
        "/checkout",
        "/pages/",
        "/blog/",
        "/about",
        "/contact",
        "/faq",
        "/size-guide",
    ]

    for pattern in non_product_patterns:
        if pattern in href_lower:
            return False

    product_indicators = [
        "/products/",
        "/product/",
        "/item/",
        "product=",
        "item=",
        "pid=",
    ]

    for indicator in product_indicators:
        if indicator in href_lower:
            return True

    base_path = urlparse(base_url).path
    href_path = urlparse(href).path

    if href_path and href_path != base_path and len(href_path.split("/")) > 2:
        return True

    return False


def extract_all_possible_selectors(html: str) -> List[str]:
    soup = get_cached_soup(html)
    selectors = set()

    for element in soup.find_all(class_=True):
        for cls in element.get("class", []):
            if cls and len(cls.strip()) > 1:
                selectors.add(f".{cls.strip()}")

    for element in soup.find_all(attrs=True):
        for attr, value in element.attrs.items():
            if isinstance(value, str) and attr.startswith("data-"):
                if any(
                    keyword in attr.lower() for keyword in ["product", "item", "goods"]
                ):
                    selectors.add(f"[{attr}]")

    for element in soup.find_all(id=True):
        element_id = element.get("id", "").strip()
        if element_id and len(element_id) > 2:
            selectors.add(f"#{element_id}")

    additional_selectors = [
        "div > div",
        "li > div",
        "article > div",
        "section > div",
        ".grid > div",
        ".list > div",
        "div",
        "li",
        "article",
        "section",
        "a",
    ]
    selectors.update(additional_selectors)

    filtered_selectors = [s for s in selectors if is_selector_promising(s)]

    logging.info(
        f"📊 Extracted {len(selectors)} total selectors, filtered to {len(filtered_selectors)} promising ones"
    )
    return filtered_selectors


def is_selector_promising(selector: str) -> bool:
    generic_selectors = ["div", "li", "a", "span", "p", "img", "button"]
    if selector in generic_selectors:
        return False

    if len(selector) < 3:
        return False

    non_product_patterns = [
        "header",
        "footer",
        "nav",
        "menu",
        "sidebar",
        "breadcrumb",
        "pagination",
        "search",
        "filter",
        "sort",
        "cart",
        "login",
    ]

    selector_lower = selector.lower()
    for pattern in non_product_patterns:
        if pattern in selector_lower:
            return False

    product_keywords = [
        "product",
        "item",
        "card",
        "grid",
        "list",
        "shop",
        "store",
        "goods",
        "merch",
        "offer",
        "deal",
        "sale",
        "price",
        "buy",
    ]

    for keyword in product_keywords:
        if keyword in selector_lower:
            return True

    if selector.startswith("[") or selector.startswith("#"):
        return True

    return True


def validate_selector_quality(
    html: str, selector: str, base_url: str
) -> Dict[str, Any]:
    soup = get_cached_soup(html)
    containers = soup.select(selector)

    if not containers:
        return {"score": 0, "reason": "No elements found"}

    product_indicators = {
        "has_name": 0,
        "has_price": 0,
        "has_image": 0,
        "has_url": 0,
        "is_likely_product": 0,
    }

    sample_size = min(SAMPLE_SIZE, len(containers))

    for i in range(sample_size):
        container = containers[i]

        name_found = check_name_presence(container)
        price_found = check_price_presence(container)
        image_found = bool(container.find("img"))
        url_found = bool(container.find("a", href=re.compile(r"product", re.I)))

        if name_found:
            product_indicators["has_name"] += 1
        if price_found:
            product_indicators["has_price"] += 1
        if image_found:
            product_indicators["has_image"] += 1
        if url_found:
            product_indicators["has_url"] += 1
        if name_found and (price_found or image_found):
            product_indicators["is_likely_product"] += 1

    score = sum(
        (product_indicators[key] / sample_size) * weight
        for key, weight in SCORE_WEIGHTS.items()
    )

    if score >= 70:
        quality = "excellent"
    elif score >= 50:
        quality = "good"
    elif score >= 30:
        quality = "poor"
    else:
        quality = "bad"

    return {
        "score": round(score, 2),
        "total_elements": len(containers),
        "indicators": product_indicators,
        "sample_tested": sample_size,
        "quality": quality,
    }


def check_name_presence(container) -> bool:
    name_selectors = [
        container.find(class_=re.compile(r"title|name|product", re.I)),
        container.find(["h1", "h2", "h3", "h4"]),
        container.find(attrs={"data-product-title": True}),
    ]
    return any(
        elem and elem.get_text(strip=True) and len(elem.get_text(strip=True)) > 2
        for elem in name_selectors
    )


def check_price_presence(container) -> bool:
    price_selectors = [
        container.find(class_=re.compile(r"price|cost|money", re.I)),
        container.find(attrs={"data-price": True}),
    ]
    return any(
        elem and re.search(r"[\$£€]?\d+\.?\d*", elem.get_text())
        for elem in price_selectors
    )


async def find_best_selector_with_validation(
    html: str,
    platform: str,
    base_url: str,
    max_selectors_to_test: int = MAX_SELECTORS_TO_TEST,
) -> Tuple[Optional[str], List[str], List[Dict], Dict[str, Any]]:
    logging.info("🎯 Starting validated selector discovery...")

    all_selectors = extract_all_possible_selectors(html)
    logging.info(f"📊 Found {len(all_selectors)} potential selectors")

    selector_scores = {}
    tested_selectors = []
    best_selector = None
    best_score = -1
    best_products = []

    for i, selector in enumerate(all_selectors[:max_selectors_to_test]):
        if i % 10 == 0:
            logging.info(
                f"   Progress: {i}/{min(len(all_selectors), max_selectors_to_test)}"
            )

        try:
            validation = validate_selector_quality(html, selector, base_url)
            selector_scores[selector] = validation
            tested_selectors.append(selector)

            if validation["score"] >= 30:
                products = extract_products_bs4(html, selector, base_url)
                valid_products = [
                    p for p in products if p.get("name") and p["name"].strip()
                ]

                combined_score = validation["score"] + min(len(valid_products) * 2, 50)

                if combined_score > best_score:
                    best_score = combined_score
                    best_selector = selector
                    best_products = valid_products
                    logging.info(
                        f"   🎯 New best: {selector} (score: {combined_score}, products: {len(valid_products)})"
                    )

        except Exception as e:
            logging.info(f"   ⚠️ Selector '{selector}' failed: {e}")
            continue

    return best_selector, tested_selectors, best_products, selector_scores


def ensure_soup(element) -> BeautifulSoup:
    return (
        element
        if isinstance(element, BeautifulSoup)
        else BeautifulSoup(str(element), "html.parser")
    )


def safe_execute(func):
    try:
        return func()
    except Exception:
        return None


def safe_select(soup, selector: str):
    try:
        return soup.select(selector)
    except Exception:
        return []


def get_text_from_element(element) -> str:
    if not element:
        return ""
    if hasattr(element, "get_text"):
        return element.get_text(strip=True)
    return str(element).strip()


def get_image_src(element) -> str:
    if not element:
        return ""
    return (
        element.get("src")
        or element.get("data-src")
        or element.get("data-lazy-src")
        or ""
    )


def extract_with_selector(soup, selector: str, value_type: str = "text") -> str:
    try:
        element = soup.select_one(selector)
        if not element:
            return ""

        if value_type == "text":
            return element.get_text(strip=True)
        elif value_type == "url":
            return element.get("href", "")
        elif value_type == "image":
            return get_image_src(element)

    except Exception:
        return ""
    return ""


def extract_name_robust(element, selectors: List[str], base_url: str) -> str:
    soup = ensure_soup(element)

    for selector in selectors:
        text = extract_with_selector(soup, selector, "text")
        if text and not is_navigation_text(text):
            logging.info(
                f"   ✅ Found name with selector '{selector}': '{text[:50]}...'"
            )
            return text

    name_patterns = [
        lambda: soup.find(class_=re.compile(r"title|name|product", re.I)),
        lambda: soup.find(["h1", "h2", "h3", "h4"]),
        lambda: soup.find(attrs={"data-product-title": True}),
        lambda: soup.find(attrs={"data-title": True}),
    ]

    for pattern in name_patterns:
        result = safe_execute(pattern)
        text = get_text_from_element(result)
        if text and not is_navigation_text(text) and len(text) < 200:
            logging.info(f"   ✅ Found name with pattern: '{text[:50]}...'")
            return text

    images = soup.find_all("img")
    for img in images:
        alt = img.get("alt", "").strip()
        if alt and not is_navigation_text(alt):
            logging.info(f"   ✅ Found name from image alt: '{alt[:50]}...'")
            return alt

    return extract_name_fallback(soup)


def extract_name_fallback(soup) -> str:
    microdata_name = soup.find(attrs={"itemprop": "name"})
    if microdata_name:
        text = microdata_name.get_text(strip=True)
        if text and not is_navigation_text(text):
            return text

    all_text = soup.get_text()
    lines = [line.strip() for line in all_text.split("\n") if line.strip()]

    candidate_lines = [
        line
        for line in lines
        if (
            10 < len(line) < 100
            and not is_navigation_text(line)
            and not re.match(r"^\$?\d+\.?\d*$", line)
        )
    ]

    if candidate_lines:
        product_keywords = ["shirt", "pants", "jacket", "dress", "shoe", "sweater"]
        for line in candidate_lines:
            if any(keyword in line.lower() for keyword in product_keywords):
                return line
        return max(candidate_lines, key=len)

    return ""


def is_valid_name(text: str) -> bool:
    """Check if text looks like a valid product name"""
    if not text or len(text.strip()) < 2:
        return False

    text_lower = text.lower().strip()

    # Skip if it's clearly a price
    if is_valid_price(text):
        return False

    # Skip navigation text
    if is_navigation_text(text):
        return False

    # Skip very short text or single words that are common in navigation
    if len(text) < 3 or (len(text.split()) == 1 and len(text) < 10):
        return False

    # Skip text that's all uppercase and short (often navigation)
    if text.isupper() and len(text) < 20:
        return False

    return True


def is_valid_price(text: str) -> bool:
    """Check if text looks like a valid price"""
    if not text:
        return False

    # Match various price formats including European (€69,95)
    price_patterns = [
        r"^[\$£€]\d+[,.]?\d*$",
        r"^\d+[,.]?\d*\s*[\$£€]?$",
        r"^[\$£€]?\s*\d+[,.]\d{2}$",
    ]

    text_clean = text.replace(" ", "").strip()
    for pattern in price_patterns:
        if re.match(pattern, text_clean):
            return True

    return False


def extract_value_by_type(element, field_type: str, base_url: str) -> str:
    """Extract value based on field type with better text handling"""
    if field_type == "text" or field_type == "name":
        text = element.get_text(strip=True)
        if text:
            text = re.sub(r"\s+", " ", text).strip()
            # Skip if it's just a number or very short
            if len(text) < 2 or text.isdigit():
                return ""
        return text if text and text not in ["", "null", "undefined"] else ""

    elif field_type == "url":
        href = element.get("href")
        if href and is_valid_product_url(href, base_url):
            return urljoin(base_url, href)
        return ""

    elif field_type == "image":
        src = get_image_src(element)
        return urljoin(base_url, src) if src else ""

    elif field_type == "price":
        text = element.get_text(strip=True)
        # More flexible price pattern matching for European formats
        price_match = re.search(r"[\$£€]?[\d,.\s]+[,.]?\d{0,2}", text)
        return price_match.group(0).strip() if price_match else ""

    return ""


def extract_product_url_robust(element, base_url: str) -> str:
    soup = ensure_soup(element)

    if soup.name == "a":
        href = soup.get("href", "").strip()
        if is_valid_product_url(href, base_url):
            full_url = urljoin(base_url, href)
            logging.info(f"   🔗 Found product URL from container: {full_url}")
            return full_url

    link_patterns = [
        'a[href*="/products/"]',
        'a[href*="/product/"]',
        'a[href*="product="]',
        'a[class*="product"]',
        'a[class*="item"]',
        "[data-product-url]",
    ]

    for pattern in link_patterns:
        links = safe_select(soup, pattern)
        for link in links:
            href = link.get("href", "").strip()
            if is_valid_product_url(href, base_url):
                full_url = urljoin(base_url, href)
                logging.info(
                    f"   🔗 Found product URL with pattern '{pattern}': {full_url}"
                )
                return full_url

    all_links = soup.find_all("a", href=True)
    for link in all_links:
        href = link.get("href", "").strip()
        if is_valid_product_url(href, base_url):
            full_url = urljoin(base_url, href)
            logging.info(f"   🔗 Found product URL from generic link: {full_url}")
            return full_url

    logging.info("   ❌ No valid product URL found")
    return ""


def extract_field_value(
    element, selectors: List[str], field_type: str = "text", base_url: str = ""
) -> str:
    soup = ensure_soup(element)

    # Special cases for URL and image fields
    if field_type == "url" and soup.name == "a":
        href = soup.get("href", "").strip()
        if href:
            full_url = urljoin(base_url, href)
            logging.info(f"   🔗 Found URL from container href: {full_url}")
            return full_url

    if field_type == "image" and soup.name == "img":
        src = get_image_src(soup)
        if src:
            full_url = urljoin(base_url, src)
            logging.info(f"   🖼️ Found image from container src: {full_url}")
            return full_url

    # Try each selector in priority order
    for selector in selectors:
        try:
            found_elements = soup.select(selector)
            if found_elements:
                for found in found_elements:
                    value = extract_value_by_type(found, field_type, base_url)
                    if value and value.strip():
                        # Additional validation for specific field types
                        if field_type == "name" and is_valid_name(value):
                            logging.info(
                                f"   ✅ Found {field_type} with selector '{selector}': {value[:50]}..."
                            )
                            return value.strip()
                        elif field_type == "price" and is_valid_price(value):
                            logging.info(
                                f"   ✅ Found {field_type} with selector '{selector}': {value[:50]}..."
                            )
                            return value.strip()
                        elif field_type != "name" and field_type != "price":
                            logging.info(
                                f"   ✅ Found {field_type} with selector '{selector}': {value[:50]}..."
                            )
                            return value.strip()
        except Exception as e:
            logging.info(f"   ⚠️ Error with selector '{selector}': {e}")
            continue

    # Special handling for name field - avoid returning prices
    if field_type == "name":
        # Try to find text that doesn't look like a price
        all_text_elements = soup.find_all(string=True)
        for text_elem in all_text_elements:
            text = text_elem.strip()
            if text and is_valid_name(text) and not is_valid_price(text):
                logging.info(f"   ✅ Found name from text analysis: {text[:50]}...")
                return text

    # For other text fields, try more aggressive text extraction
    if field_type == "text":
        text = soup.get_text(strip=True)
        if text and len(text) > 2 and not is_navigation_text(text):
            logging.info(f"   ✅ Found text from element: {text[:50]}...")
            return text

    # Final fallbacks
    return apply_field_fallback(soup, field_type, base_url)


def extract_value_by_type(element, field_type: str, base_url: str) -> str:
    """Extract value based on field type with better text handling"""
    if field_type == "text":
        text = element.get_text(strip=True)
        # Clean up the text - remove extra whitespace and common noise
        if text:
            text = re.sub(r"\s+", " ", text).strip()
            # Skip if it's just a number or very short
            if len(text) < 2 or text.isdigit():
                return ""
        return text if text and text not in ["", "null", "undefined"] else ""

    elif field_type == "url":
        href = element.get("href")
        if href and is_valid_product_url(href, base_url):
            return urljoin(base_url, href)
        return ""

    elif field_type == "image":
        src = get_image_src(element)
        return urljoin(base_url, src) if src else ""

    elif field_type == "price":
        text = element.get_text(strip=True)
        # More flexible price pattern matching
        price_match = re.search(r"[\$£€]?[\d,.]+\.?\d*", text)
        return price_match.group(0) if price_match else ""

    return ""


def apply_field_fallback(soup, field_type: str, base_url: str) -> str:
    """Apply final fallback strategies for field extraction"""
    if field_type == "url":
        # Look for any link that might be a product link
        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            if is_valid_product_url(href, base_url):
                full_url = urljoin(base_url, href)
                logging.info(f"   🔗 Fallback URL found: {full_url}")
                return full_url

    elif field_type == "image":
        # Look for any image
        images = soup.find_all("img")
        for img in images:
            src = get_image_src(img)
            if src:
                full_url = urljoin(base_url, src)
                logging.info(f"   🖼️ Fallback image found: {full_url}")
                return full_url

    elif field_type == "text":
        # Try to extract meaningful text from the container
        text = soup.get_text(strip=True)
        if text and len(text) > 2 and not is_navigation_text(text):
            # Clean and return the text
            text = re.sub(r"\s+", " ", text).strip()
            logging.info(f"   📝 Fallback text found: {text[:50]}...")
            return text

    logging.info(f"   ❌ No {field_type} found with any strategy")
    return ""


async def local_llm_call(prompt: str, model: str = "deepseek-coder-v2:16b") -> str:
    url = "http://localhost:11434/api/generate"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json={"model": model, "prompt": prompt, "stream": False}
        ) as resp:
            data = await resp.json()
            return data.get("response", "").strip()


async def analyze_product_structure_with_llm(
    html: str, top_selectors: List[str], platform: str, sample_size: int = SAMPLE_SIZE
) -> Dict[str, Any]:
    logging.info("🤖 Using LLM to analyze product structure...")

    soup = get_cached_soup(html)
    selector_samples = {}

    for selector in top_selectors[:5]:
        containers = soup.select(selector)
        if containers:
            sample_html = ""
            for i, container in enumerate(containers[:sample_size]):
                sample_html += f"\n--- {selector} - Element {i + 1} ---\n"
                sample_html += str(container.prettify())[:800]
            selector_samples[selector] = sample_html

    prompt = f"""
You are an expert in e-commerce HTML structure analysis.

PLATFORM: {platform}
TOP SELECTORS BEING EVALUATED:
{json.dumps(top_selectors, indent=2)}

HTML SAMPLES OF TOP SELECTORS:
{json.dumps(selector_samples, indent=2)}

ANALYSIS TASK:
1. Analyze which selectors are most likely to be ACTUAL PRODUCT CONTAINERS
2. Look for indicators of real products:
   - Product names/titles
   - Prices (with currency symbols)
   - Product images
   - "Add to cart" buttons
   - Product descriptions
   - Links to individual product pages
3. Identify which selectors contain complete product information vs partial/navigation elements
4. Rank them from best to worst for actual product extraction

CRITICAL: Avoid selectors that match:
- Navigation menus
- Category links
- Header/footer elements
- Non-product promotional content

Return a JSON object with this structure:
{{
    "ranked_selectors": ["best_selector", "second_best", ...],
    "analysis": "Brief explanation of why the top selector works best",
    "confidence": 0.85,
    "product_indicators_found": ["name", "price", "image", "url"]
}}

Return ONLY the JSON object.
"""

    try:
        response = await local_llm_call(prompt)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            analysis = json.loads(match.group(0))
            logging.info(f"✅ LLM product structure analysis complete")
            return analysis
    except Exception as e:
        logging.info(f"❌ LLM product structure analysis failed: {e}")

    return {"ranked_selectors": top_selectors, "confidence": 0.5}


async def analyze_selectors_with_llm(
    html: str, selector_stats: Dict[str, int], platform: str, top_k: int = 20
) -> List[str]:
    logging.info("🤖 Using LLM to analyze selector performance...")

    sorted_selectors = sorted(selector_stats.items(), key=lambda x: x[1], reverse=True)
    top_selectors = [
        selector for selector, count in sorted_selectors[:top_k] if count > 0
    ]

    if not top_selectors:
        return []

    soup = get_cached_soup(html)
    selector_samples = {}

    for selector in top_selectors[:5]:
        elements = soup.select(selector)
        if elements:
            sample_html = ""
            for i, element in enumerate(elements[:2]):
                sample_html += f"\n--- {selector} - Element {i + 1} ---\n"
                sample_html += str(element.prettify())[:500]
            selector_samples[selector] = sample_html

    prompt = f"""
You are an expert in e-commerce HTML structure analysis.

PLATFORM: {platform}
TOP SELECTORS AND THEIR PRODUCT COUNTS:
{json.dumps(dict(sorted_selectors[:top_k]), indent=2)}

HTML SAMPLES OF TOP SELECTORS:
{json.dumps(selector_samples, indent=2)}

ANALYSIS TASK:
1. Analyze which selectors are most likely to be actual product containers
2. Consider: specificity, product structure, platform patterns
3. Rank the selectors from best to worst for product extraction
4. Explain why certain selectors work better than others

CRITERIA FOR GOOD PRODUCT SELECTORS:
- Should match multiple similar elements (products)
- Should contain complete product information (name, price, image, link)
- Should not be too generic (matching non-product elements)
- Should be specific enough to avoid nested elements

RETURN FORMAT:
{{
    "ranked_selectors": ["best_selector", "second_best", ...],
    "analysis": "Brief explanation of why the top selectors work well",
    "confidence_score": 0.85
}}

Return ONLY the JSON object.
"""

    try:
        response = await local_llm_call(prompt)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            analysis = json.loads(match.group(0))
            ranked_selectors = analysis.get("ranked_selectors", [])
            logging.info(
                f"✅ LLM analysis complete. Top selector: {ranked_selectors[0] if ranked_selectors else 'None'}"
            )
            return ranked_selectors
    except Exception as e:
        logging.info(f"❌ LLM selector analysis failed: {e}")

    return [selector for selector, count in sorted_selectors if count > 0]


async def generate_selectors_with_llm(html: str, platform: str) -> List[str]:
    prompt = f"""
You are an expert in e-commerce HTML parsing.
HTML snippet (truncated): {html[:5000]}
Platform: {platform}

Analyze this HTML and return a JSON array of the 10 most likely CSS selectors for product containers.
Focus on selectors that:
1. Match multiple similar elements
2. Contain product images, names, prices
3. Are specific to product containers, not wrappers
4. Work for the detected platform

Return ONLY the JSON array of strings.
"""

    try:
        response = await local_llm_call(prompt)
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            selectors = json.loads(match.group(0))
            return [s.strip() for s in selectors if s.strip()]
    except Exception:
        pass

    return []


def infer_platform(html: str, url: str) -> str:
    html_lower = html.lower()
    if "cdn.shopify.com" in html_lower or "shopify" in url:
        return "Shopify"
    elif "woocommerce" in html_lower:
        return "WooCommerce"
    return "Custom"


def extract_products_bs4(html: str, selector: str, base_url: str) -> List[Dict]:
    soup = get_cached_soup(html)
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

            products.append(
                {
                    "name": name,
                    "url": url,
                }
            )
        except Exception as e:
            logging.info(f"⚠️ Skipping malformed product: {e}")

    return products


async def test_selectors_exhaustive(
    html: str, base_url: str, max_test_count: int = 50, min_products: int = 2
) -> Tuple[str, List[str], List[Dict], Dict[str, int]]:
    selectors = extract_all_possible_selectors(html)
    logging.info(f"🧪 Testing {len(selectors)} selectors (max {max_test_count})...")

    best_selector = None
    best_products = []
    tested_selectors = []
    selector_stats = {}

    test_batch = selectors[:max_test_count]

    for i, selector in enumerate(test_batch):
        if i % 10 == 0:
            logging.info(f"   Progress: {i}/{len(test_batch)}")

        try:
            products = extract_products_bs4(html, selector, base_url)
            valid_products = [
                p for p in products if p.get("name") and p["name"].strip()
            ]

            selector_stats[selector] = len(valid_products)
            tested_selectors.append(selector)

            if len(valid_products) > len(best_products):
                best_products = valid_products
                best_selector = selector
                logging.info(
                    f"   ✅ New best: {selector} → {len(valid_products)} products"
                )

            if len(valid_products) >= 10:
                logging.info(f"   🎉 Found excellent selector early: {selector}")
                break

        except Exception as e:
            selector_stats[selector] = 0
            continue

    return best_selector, tested_selectors, best_products, selector_stats


async def hybrid_selector_discovery(
    html: str,
    platform: str,
    base_url: str,
    strategy: str = "smart",
) -> Tuple[str, List[str], List[Dict]]:
    logging.info(f"🎯 Starting hybrid selector discovery (strategy: {strategy})")

    if strategy == "llm_first":
        llm_selectors = await generate_selectors_with_llm(html, platform)
        for selector in llm_selectors:
            products = extract_products_bs4(html, selector, base_url)
            if len(products) >= 2:
                return selector, [selector], products

        (
            best_selector,
            tested_selectors,
            best_products,
            _,
        ) = await test_selectors_exhaustive(html, base_url)
        return best_selector, tested_selectors, best_products

    elif strategy == "exhaustive":
        (
            best_selector,
            tested_selectors,
            best_products,
            _,
        ) = await test_selectors_exhaustive(html, base_url)
        return best_selector, tested_selectors, best_products

    else:
        (
            best_selector,
            tested_selectors,
            best_products,
            stats,
        ) = await test_selectors_exhaustive(html, base_url, max_test_count=30)

        if best_products and len(best_products) >= 2:
            llm_ranked = await analyze_selectors_with_llm(html, stats, platform)
            if llm_ranked:
                llm_top_selector = llm_ranked[0]
                if llm_top_selector != best_selector:
                    llm_products = extract_products_bs4(
                        html, llm_top_selector, base_url
                    )
                    if len(llm_products) > len(best_products):
                        logging.info(
                            f"🎯 LLM improved selector: {llm_top_selector} → {len(llm_products)} products"
                        )
                        best_selector = llm_top_selector
                        best_products = llm_products

        return best_selector, tested_selectors, best_products


async def find_valid_selector(
    html: str, platform: str, base_url: str, max_attempts: int = 5
) -> Tuple[str, List[str], List[Dict]]:
    logging.info("🎯 Starting validated selector discovery...")

    (
        best_selector,
        tested_selectors,
        best_products,
        selector_scores,
    ) = await find_best_selector_with_validation(
        html, platform, base_url, max_selectors_to_test=50
    )

    if best_selector and selector_scores:
        scored_selectors = [
            (sel, score["score"])
            for sel, score in selector_scores.items()
            if score["score"] >= 20
        ]
        scored_selectors.sort(key=lambda x: x[1], reverse=True)
        top_selectors = [sel for sel, score in scored_selectors[:5]]

        if top_selectors:
            llm_analysis = await analyze_product_structure_with_llm(
                html, top_selectors, platform
            )
            llm_ranked = llm_analysis.get("ranked_selectors", [])

            if llm_ranked:
                llm_top_selector = llm_ranked[0]
                if llm_top_selector != best_selector:
                    validation = validate_selector_quality(
                        html, llm_top_selector, base_url
                    )
                    if validation["score"] >= 30:
                        llm_products = extract_products_bs4(
                            html, llm_top_selector, base_url
                        )
                        valid_llm_products = [
                            p
                            for p in llm_products
                            if p.get("name") and p["name"].strip()
                        ]

                        if len(valid_llm_products) >= len(best_products):
                            logging.info(
                                f"🎯 LLM improved selector: {llm_top_selector}"
                            )
                            logging.info(
                                f"   Quality: {validation['quality']}, Products: {len(valid_llm_products)}"
                            )
                            best_selector = llm_top_selector
                            best_products = valid_llm_products

    if not best_products:
        logging.info("🔄 Validated approach failed, trying fallback selectors...")
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

        for selector in fallback_selectors:
            if selector in tested_selectors:
                continue

            validation = validate_selector_quality(html, selector, base_url)
            if validation["score"] >= 20:
                tested_selectors.append(selector)
                products = extract_products_bs4(html, selector, base_url)
                valid_products = [
                    p for p in products if p.get("name") and p["name"].strip()
                ]

                if len(valid_products) > len(best_products):
                    best_products = valid_products
                    best_selector = selector
                    logging.info(f"✅ Validated fallback selector: {selector}")
                    logging.info(
                        f"   Quality: {validation['quality']}, Products: {len(valid_products)}"
                    )
                    break

    if best_products:
        final_validation = validate_selector_quality(html, best_selector, base_url)
        logging.info(f"🎉 Final selector: {best_selector}")
        logging.info(
            f"   Quality: {final_validation['quality']} (score: {final_validation['score']})"
        )
        logging.info(f"   Products found: {len(best_products)}")
        logging.info(f"   Total elements: {final_validation['total_elements']}")

        for i, product in enumerate(best_products[:2]):
            logging.info(
                f"   Sample {i + 1}: {product.get('name', 'N/A')} - {product.get('price', 'N/A')}"
            )
    else:
        logging.info("❌ No valid product selector found")

    return best_selector, tested_selectors, best_products


async def detect_field_selectors(
    html: str, platform: str, product_selector: str
) -> Dict[str, List[str]]:
    logging.info("🤖 Starting LLM field selector detection...")

    soup = get_cached_soup(html)
    sample_containers = soup.select(product_selector)

    if sample_containers:
        sample_html = ""
        for i, container in enumerate(sample_containers[:3]):
            sample_html += f"\n--- Product {i + 1} ---\n"
            sample_html += str(container.prettify())[:1000]
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
        logging.info("📤 Sending request to LLM...")
        response = await local_llm_call(prompt)
        logging.info(f"📥 LLM raw response: {response}")

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            selectors = json.loads(match.group(0))
            logging.info(f"✅ LLM returned field selectors: {selectors}")

            expected_fields = ["name", "price", "image", "description", "url"]
            validated_selectors = {}

            for field in expected_fields:
                field_sel = selectors.get(field, [])
                if not field_sel:
                    field_sel = []
                elif isinstance(field_sel, str):
                    field_sel = [field_sel]

                validated_selectors[field] = field_sel

            return validated_selectors
        else:
            logging.info("❌ No JSON found in LLM response")
    except Exception as e:
        logging.info(f"❌ LLM field selector detection failed: {e}")

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
    logging.info(f"🔄 Using fallback selectors: {fallback}")
    return fallback


def extract_price_specialized(element) -> str:
    soup = ensure_soup(element)

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

    price_attrs = ["data-price", "data-product-price", "data-item-price"]
    for attr in price_attrs:
        price = soup.find(attrs={attr: True})
        if price:
            return price[attr]

    return ""


def check_availability(element) -> bool:
    soup = ensure_soup(element)

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

    in_stock_indicators = [
        ".in-stock",
        ".available",
        '[class*="in-stock"]',
        ".add-to-cart",
    ]

    for selector in in_stock_indicators:
        if soup.select_one(selector):
            return True

    return True


def extract_products_bs4_enhanced(
    html: str,
    selector: str,
    base_url: str,
    platform: str = "Custom",
    field_selectors: Dict[str, List[str]] | None = None,
) -> List[Dict]:
    logging.info(f"🔍 Starting enhanced extraction with selector: {selector}")
    soup = get_cached_soup(html)
    containers = soup.select(selector)
    logging.info(f"📦 Found {len(containers)} product containers")

    if not containers:
        logging.info("❌ No containers found with selector:", selector)
        return []

    if not field_selectors:
        logging.info("🤖 Using default field selectors...")
        field_selectors = {
            "name": FIELD_EXTRACTION_PRIORITIES["name"],
            "price": FIELD_EXTRACTION_PRIORITIES["price"],
            "image": FIELD_EXTRACTION_PRIORITIES["image"],
            "url": FIELD_EXTRACTION_PRIORITIES["url"],
            "description": ["p", ".description", "[class*='desc']", ".product-desc"],
        }
    else:
        logging.info("⚡ Using cached field selectors")

    logging.info(f"🎯 Field selectors: {field_selectors}")

    if containers:
        first_container = containers[0]
        logging.info(f"🔎 First container HTML structure:")
        logging.info(
            f"   Text preview: {first_container.get_text(strip=True)[:100]}..."
        )
        logging.info(f"   Classes: {first_container.get('class', [])}")
        logging.info(f"   Tag: {first_container.name}")

        logging.info(f"🧪 Testing field selectors on first container:")
        for field, selectors in field_selectors.items():
            for sel in selectors[:2]:
                try:
                    found = first_container.select_one(sel)
                    if found:
                        if field == "image":
                            src = found.get("src") or found.get("data-src")
                            logging.info(
                                f"   ✅ {field} selector '{sel}': FOUND (src: {src})"
                            )
                        else:
                            text = found.get_text(strip=True)
                            logging.info(
                                f"   ✅ {field} selector '{sel}': FOUND ('{text[:50]}...')"
                            )
                    else:
                        logging.info(f"   ❌ {field} selector '{sel}': NOT FOUND")
                except Exception as e:
                    logging.info(f"   ⚠️ {field} selector '{sel}': ERROR - {e}")

    products = []
    successful_extractions = 0

    for i, product in enumerate(containers):
        try:
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

            if not price:
                price = extract_price_specialized(product)

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
                if i == 0:
                    logging.info(f"   ❌ Skipping product - name: '{name}'")

        except Exception as e:
            if i == 0:
                logging.info(f"⚠️ Error processing product: {e}")
            continue

    logging.info(
        f"🏁 Extraction complete: {successful_extractions}/{len(containers)} products successfully extracted"
    )

    if successful_extractions == 0:
        logging.info(
            "🔄 Enhanced extraction failed, falling back to basic extraction..."
        )
        basic_products = extract_products_bs4(html, selector, base_url)
        logging.info(f"📦 Basic extraction found: {len(basic_products)} products")
        return basic_products

    final_products = ensure_serializable_products(products)
    return final_products
