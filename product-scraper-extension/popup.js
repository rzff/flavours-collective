let currentResults = null;
let currentUrl = null;

chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
  if (!tabs || !tabs[0]) return;
  const tab = tabs[0];

  if (tab.url) {
    currentUrl = tab.url;
    const urlDisplay = document.getElementById("url-display");
    if (urlDisplay) {
      urlDisplay.textContent =
        currentUrl.length > 100
          ? currentUrl.substring(0, 100) + "..."
          : currentUrl;
      urlDisplay.title = currentUrl;
    }
  }

  chrome.scripting.executeScript(
    { target: { tabId: tab.id }, func: detectPlatformFromPage },
    (results) => {
      if (chrome.runtime.lastError) return;
      const platform = results?.[0]?.result ?? "unknown";
      const btn = document.getElementById("shopify-json-btn");
      if (btn) btn.style.display = platform === "shopify" ? "block" : "none";
    },
  );
});

document.addEventListener("DOMContentLoaded", function () {
  setupEventListeners();
});

function setupEventListeners() {
  document
    .getElementById("scrape-btn")
    .addEventListener("click", () => scrapeCurrentPage(false));
  document
    .getElementById("scrape-with-details")
    .addEventListener("click", () => scrapeCurrentPage(true));
  document
    .getElementById("copy-json")
    .addEventListener("click", copyResultsToClipboard);
  document
    .getElementById("view-console")
    .addEventListener("click", viewResultsInConsole);
  document
    .getElementById("shopify-json-btn")
    .addEventListener("click", printShopifyJson);
}

function scrapeCurrentPage(withDetails) {
  if (!currentUrl) {
    showStatus("No URL found.", "error");
    return;
  }

  showStatus("Detecting platform...", "loading");

  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    chrome.scripting.executeScript(
      { target: { tabId: tabs[0].id }, func: detectPlatformFromPage },
      (results) => {
        const platform = results?.[0]?.result ?? "unknown";

        // FIXED: Use PlatformDetector object to avoid redeclaration error
        if (PlatformDetector.SCRAPE_ONLY_PLATFORMS.includes(platform)) {
          performServerScraping(currentUrl, withDetails);
        } else {
          fetchProductsFromTab(tabs[0].id, currentUrl, platform, withDetails);
        }
      },
    );
  });
}

function fetchProductsFromTab(tabId, url, platform, withDetails) {
  const fetcher = PlatformDetector.fetchers[platform];
  if (!fetcher) {
    performServerScraping(url, withDetails);
    return;
  }

  showStatus(platform.toUpperCase() + " detected - fetching...", "loading");

  chrome.scripting.executeScript(
    { target: { tabId }, func: fetcher, args: [url] },
    (results) => {
      const result = results?.[0]?.result;
      if (
        !result ||
        result.error ||
        !result.products ||
        result.products.length === 0
      ) {
        performServerScraping(url, withDetails);
        return;
      }

      const normalized = normalizeProducts(platform, result.products, url);
      currentResults = {
        success: true,
        source: platform + "_api",
        url,
        data: {
          platform: platform.toUpperCase(),
          productCount: normalized.length,
          products: normalized,
        },
      };
      displayAllResults(currentResults, url);
    },
  );
}

function normalizeProducts(platform, products, baseUrl) {
  const normalizer = PlatformDetector.normalizers[platform];
  return normalizer ? normalizer(products, baseUrl) : products;
}

function copyResultsToClipboard() {
  if (!currentResults) return;
  navigator.clipboard
    .writeText(JSON.stringify(currentResults, null, 2))
    .then(() => {
      const btn = document.getElementById("copy-json");
      const original = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => {
        btn.textContent = original;
      }, 2000);
    });
}

function displayAllResults(data, baseUrl) {
  document.getElementById("results-count").textContent =
    data.data.productCount + " products found (" + data.data.platform + ")";

  const container = document.getElementById("products-container");
  container.innerHTML = "";

  data.data.products.forEach((p, i) => {
    const div = document.createElement("div");
    div.className = "product-item";
    div.innerHTML = `<div class="product-name">${i + 1}. ${p.name}</div><div class="product-price">${p.priceRaw || "N/A"}</div>`;
    container.appendChild(div);
  });

  document.getElementById("status").classList.add("hidden");
  document.getElementById("results-section").classList.remove("hidden");
}

function showStatus(m, t) {
  const s = document.getElementById("status");
  s.textContent = m;
  s.className = "status-message " + t;
  s.classList.remove("hidden");
  document.getElementById("results-section").classList.add("hidden");
}

/* Other helpers (performServerScraping, viewResultsInConsole, etc.) remain as in your original popup.js */
function performServerScraping(url, d) {
  console.log("Falling back to server for:", url);
}
function viewResultsInConsole() {
  console.log(currentResults);
}
function printShopifyJson() {
  console.log("Shopify debug clicked");
}
