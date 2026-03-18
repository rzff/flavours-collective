let currentResults = null;
let currentUrl = null;

// 1. Initial Setup: Get URL and Platform
chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
  if (!tabs || !tabs[0]) return;
  const tab = tabs[0];
  currentUrl = tab.url;

  const urlDisplay = document.getElementById("url-display");
  if (urlDisplay) {
    urlDisplay.textContent =
      currentUrl.length > 70 ? currentUrl.substring(0, 70) + "..." : currentUrl;
  }

  chrome.scripting.executeScript(
    { target: { tabId: tab.id }, func: detectPlatformFromPage },
    (results) => {
      if (chrome.runtime.lastError) return;
      const platform = results?.[0]?.result ?? "unknown";
      console.log("Detected platform:", platform);
    },
  );
});

// 2. Event Listeners
document.addEventListener("DOMContentLoaded", function () {
  document
    .getElementById("scrape-btn")
    .addEventListener("click", () => startScrape());
  document
    .getElementById("copy-json")
    .addEventListener("click", copyToClipboard);
});

// 3. The Core Scrape Logic
function startScrape() {
  showStatus("Detecting Platform...", "loading");

  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    const tab = tabs[0];

    chrome.scripting.executeScript(
      { target: { tabId: tab.id }, func: detectPlatformFromPage },
      (results) => {
        const platform = results?.[0]?.result ?? "unknown";

        // ROUTE A: Local Extension Scraping (Shopify, Woo, etc.)
        if (!PlatformDetector.SCRAPE_ONLY_PLATFORMS.includes(platform)) {
          showStatus(`Fetching ${platform} data locally...`, "loading");
          const fetcher = PlatformDetector.fetchers[platform];

          chrome.scripting.executeScript(
            { target: { tabId: tab.id }, func: fetcher, args: [currentUrl] },
            (fetchResults) => {
              const result = fetchResults?.[0]?.result;
              if (result && !result.error) {
                const normalized = PlatformDetector.normalizers[platform](
                  result.products,
                  currentUrl,
                );

                currentResults = {
                  success: true,
                  source: "extension_api",
                  url: currentUrl,
                  data: {
                    platform: platform.toUpperCase(),
                    productCount: normalized.length,
                    products: normalized,
                  },
                };

                displayResults(currentResults);
                sendDataToSpringBoot(currentResults); // Save to DB
              } else {
                showStatus(
                  "Local Fetch failed. Try server-side scrape.",
                  "error",
                );
              }
            },
          );
        }
        // ROUTE B: Server-Side Scraping (FastAPI / Crawl4AI)
        else {
          showStatus("Handing off to Server-Side Scraper...", "loading");
          triggerServerSideScrape(currentUrl);
        }
      },
    );
  });
}

// 4. Bridge for Local Data -> DB
async function sendDataToSpringBoot(results) {
  try {
    const response = await fetch("http://localhost:8080/api/scraping/store", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(results),
    });

    if (response.ok) {
      showStatus(
        `Saved ${results.data.productCount} products to DB!`,
        "success",
      );
    } else {
      showStatus("Storage Error: " + response.status, "error");
    }
  } catch (err) {
    showStatus("Connection Refused (Spring Boot down?)", "error");
  }
}

// 5. Bridge for URL -> Server Scrape -> DB
async function triggerServerSideScrape(url) {
  try {
    const response = await fetch(
      "http://localhost:8080/api/scraping/products",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url }),
      },
    );

    if (response.ok) {
      const result = await response.json();

      // Map server response to a UI-friendly format
      const count = result.products ? result.products.length : 0;

      currentResults = result;
      displayResults({
        data: { productCount: count },
      });

      showStatus(`Server Scraped & Saved ${count} products!`, "success");
    } else {
      showStatus("Server-Side Error: " + response.status, "error");
    }
  } catch (err) {
    showStatus("Could not connect to Orchestrator.", "error");
  }
}

// --- UI Helpers ---

function displayResults(data) {
  const count = data.data ? data.data.productCount : 0;
  document.getElementById("results-count").textContent =
    count + " products found";
  document.getElementById("results-section").classList.remove("hidden");
  document.getElementById("status").classList.add("hidden");
}

function showStatus(msg, type) {
  const s = document.getElementById("status");
  s.textContent = msg;
  s.className = "status-message " + type;
  s.classList.remove("hidden");
}

function copyToClipboard() {
  if (!currentResults) return;
  navigator.clipboard.writeText(JSON.stringify(currentResults, null, 2));
  alert("JSON Copied!");
}
