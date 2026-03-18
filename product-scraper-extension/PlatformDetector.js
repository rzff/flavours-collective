// =============================================================================
// platformDetector.js
// Detects the webshop platform from within the active tab and fetches
// product data via the platform's public API where available.
// Runs as an injected content script — has access to window and document.
// =============================================================================

// -----------------------------------------------------------------------------
// Detection — runs inside the tab
// -----------------------------------------------------------------------------

function detectPlatformFromPage() {
  if (window.Shopify && window.Shopify.shop) return "shopify";
  if (window.ShopifyAnalytics) return "shopify";
  const scripts = Array.from(document.querySelectorAll("script[src]"));
  if (scripts.some((s) => s.src.includes("cdn.shopify.com"))) return "shopify";

  if (window.woocommerce_params || window.wc_cart_params) return "woocommerce";
  if (window.wcSettings) return "woocommerce";
  if (document.body.classList.contains("woocommerce")) return "woocommerce";

  if (window.require && window.MAGE_URLS) return "magento";
  const magentoMeta = document.querySelector('meta[name="generator"]');
  if (magentoMeta && magentoMeta.content.toLowerCase().includes("magento"))
    return "magento";
  if (document.querySelector('script[type="text/x-magento-init"]'))
    return "magento";

  if (window.BCData) return "bigcommerce";
  if (window.bcAnalyticsSettings) return "bigcommerce";
  const bcMeta = document.querySelector('meta[name="generator"]');
  if (bcMeta && bcMeta.content.toLowerCase().includes("bigcommerce"))
    return "bigcommerce";

  if (window.prestashop) return "prestashop";
  const psMeta = document.querySelector('meta[name="generator"]');
  if (psMeta && psMeta.content.toLowerCase().includes("prestashop"))
    return "prestashop";

  if (window.Static && window.Static.SQUARESPACE_CONTEXT) return "squarespace";
  if (document.querySelector('meta[generator*="Squarespace"]'))
    return "squarespace";
  if (scripts.some((s) => s.src.includes("squarespace.com")))
    return "squarespace";

  if (window.wixBiSession) return "wix";
  if (
    scripts.some(
      (s) => s.src.includes("wix.com") || s.src.includes("wixstatic.com"),
    )
  )
    return "wix";

  if (window.Webflow) return "webflow";
  if (scripts.some((s) => s.src.includes("webflow.com"))) return "webflow";

  if (document.querySelector('link[rel="https://api.w.org/"]'))
    return "woocommerce";

  return "unknown";
}

// --- API fetchers ---

async function fetchShopifyProducts(collectionUrl) {
  try {
    const parsed = new URL(collectionUrl);
    const match = parsed.pathname.match(/^(\/collections\/[^/]+)/);
    const endpoint = match
      ? `${parsed.origin}${match[1]}/products.json?limit=250`
      : `${parsed.origin}/products.json?limit=250`;
    const response = await fetch(endpoint, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return { error: `HTTP ${response.status}`, endpoint };
    const data = await response.json();
    return { products: data.products || [], endpoint, raw: data };
  } catch (err) {
    return { error: err.message };
  }
}

async function fetchWooCommerceProducts(pageUrl) {
  const origin = new URL(pageUrl).origin;
  const storeApiUrl = `${origin}/wp-json/wc/store/v1/products?per_page=100`;
  try {
    const response = await fetch(storeApiUrl, {
      headers: { Accept: "application/json" },
    });
    if (response.ok) {
      const data = await response.json();
      return {
        products: Array.isArray(data) ? data : [],
        endpoint: storeApiUrl,
        raw: data,
      };
    }
  } catch (_) {}
  return { error: "No accessible WooCommerce API found", products: [] };
}

async function fetchMagentoProducts(pageUrl) {
  const origin = new URL(pageUrl).origin;
  const endpoint = `${origin}/rest/V1/products?searchCriteria[filter_groups][0][filters][0][field]=visibility&searchCriteria[filter_groups][0][filters][0][value]=4&searchCriteria[pageSize]=50`;
  try {
    const response = await fetch(endpoint, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return { error: `HTTP ${response.status}`, products: [] };
    const data = await response.json();
    return { products: data.items || [], endpoint, raw: data };
  } catch (err) {
    return { error: err.message, products: [] };
  }
}

async function fetchBigCommerceProducts(pageUrl) {
  const origin = new URL(pageUrl).origin;
  const endpoint = `${origin}/api/storefront/products?limit=50&include=images,variants`;
  try {
    const response = await fetch(endpoint, {
      headers: {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    if (!response.ok) return { error: `HTTP ${response.status}`, products: [] };
    const data = await response.json();
    return {
      products: Array.isArray(data) ? data : data.data || [],
      endpoint,
      raw: data,
    };
  } catch (err) {
    return { error: err.message, products: [] };
  }
}

async function fetchPrestaShopProducts(pageUrl) {
  const origin = new URL(pageUrl).origin;
  const endpoint = `${origin}/api/products?output_format=JSON&limit=50`;
  try {
    const response = await fetch(endpoint, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok)
      return {
        error: `HTTP ${response.status}`,
        products: [],
        requiresAuth: true,
      };
    const data = await response.json();
    return { products: data.products || [], endpoint, raw: data };
  } catch (err) {
    return { error: err.message, products: [], requiresAuth: true };
  }
}

// --- Normalizers ---

function normalizeShopify(products, baseUrl) {
  const origin = new URL(baseUrl).origin;
  return products.map((p) => ({
    platform: "shopify",
    name: p.title,
    handle: p.handle,
    productId: String(p.id),
    url: `${origin}/products/${p.handle}`,
    priceRaw: p.variants?.[0]?.price ?? null,
    priceValue: p.variants?.[0]?.price ? parseFloat(p.variants[0].price) : null,
    inStock: p.variants?.some((v) => v.available) ?? false,
    imageUrl: p.images?.[0]?.src ?? null,
    imageUrls: p.images?.map((img) => img.src) ?? [],
  }));
}

function normalizeWooCommerce(products, baseUrl) {
  return products.map((p) => ({
    platform: "woocommerce",
    name: p.name || (p.title?.rendered ?? "Unknown"),
    productId: String(p.id),
    url: p.permalink || p.link,
    priceRaw: p.prices?.price
      ? (parseInt(p.prices.price) / 100).toFixed(2)
      : null,
    inStock: p.is_in_stock ?? null,
    imageUrl: p.images?.[0]?.src ?? p.featured_media_src_url ?? null,
  }));
}

function normalizeMagento(products, baseUrl) {
  const origin = new URL(baseUrl).origin;
  return products.map((p) => {
    const imgAttr = p.custom_attributes?.find(
      (a) => a.attribute_code === "thumbnail",
    );
    return {
      platform: "magento",
      name: p.name,
      productId: String(p.id),
      priceRaw: p.price ? String(p.price) : null,
      imageUrl: imgAttr
        ? `${origin}/pub/media/catalog/product${imgAttr.value}`
        : null,
    };
  });
}

function normalizeBigCommerce(products, baseUrl) {
  const origin = new URL(baseUrl).origin;
  return products.map((p) => ({
    platform: "bigcommerce",
    name: p.name,
    productId: String(p.id || p.productId),
    url: p.url ? `${origin}${p.url}` : null,
    priceRaw: p.price?.without_tax?.formatted ?? String(p.price?.value || ""),
    imageUrl: p.main_image?.data ?? p.images?.[0]?.data ?? null,
  }));
}

function normalizePrestaShop(products) {
  return products.map((p) => ({
    platform: "prestashop",
    name: p.name ?? "Unknown",
    productId: String(p.id),
    priceRaw: p.price ? String(p.price) : null,
    inStock: p.active === "1",
  }));
}

const SCRAPE_ONLY_PLATFORMS = ["squarespace", "wix", "webflow", "unknown"];

const PlatformDetector = {
  SCRAPE_ONLY_PLATFORMS,
  detectPlatformFromPage,
  fetchers: {
    shopify: fetchShopifyProducts,
    woocommerce: fetchWooCommerceProducts,
    magento: fetchMagentoProducts,
    bigcommerce: fetchBigCommerceProducts,
    prestashop: fetchPrestaShopProducts,
  },
  normalizers: {
    shopify: normalizeShopify,
    woocommerce: normalizeWooCommerce,
    magento: normalizeMagento,
    bigcommerce: normalizeBigCommerce,
    prestashop: normalizePrestaShop,
  },
};
