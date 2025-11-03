let currentResults = null;
let currentUrl = null;

document.addEventListener("DOMContentLoaded", function () {
  // Get URL immediately without waiting for tab query
  updateCurrentUrlFast();
  setupEventListeners();
});

function updateCurrentUrlFast() {
  const urlDisplay = document.getElementById("url-display");
  urlDisplay.textContent = "Getting current page...";

  // Use a more efficient approach
  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    if (tabs && tabs[0] && tabs[0].url) {
      currentUrl = tabs[0].url;
      const displayUrl =
        currentUrl.length > 100
          ? currentUrl.substring(0, 100) + "..."
          : currentUrl;
      urlDisplay.textContent = displayUrl;
      urlDisplay.title = currentUrl;
    } else {
      urlDisplay.textContent = "Unable to get current URL";
      urlDisplay.style.color = "#dc3545";
    }
  });
}

function setupEventListeners() {
  document.getElementById("scrape-btn").addEventListener("click", function () {
    scrapeCurrentPage(false);
  });

  document
    .getElementById("scrape-with-details")
    .addEventListener("click", function () {
      scrapeCurrentPage(true);
    });

  document
    .getElementById("copy-json")
    .addEventListener("click", copyResultsToClipboard);
  document
    .getElementById("view-console")
    .addEventListener("click", viewResultsInConsole);
}

function scrapeCurrentPage(withDetails) {
  // Use the already stored URL or get it fresh
  if (!currentUrl) {
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      if (tabs && tabs[0] && tabs[0].url) {
        currentUrl = tabs[0].url;
        performScraping(currentUrl, withDetails);
      } else {
        showStatus("❌ No URL found. Please try again.", "error");
      }
    });
  } else {
    performScraping(currentUrl, withDetails);
  }
}

function performScraping(url, withDetails) {
  if (!isValidUrl(url)) {
    showStatus("❌ Invalid URL. Please navigate to a valid website.", "error");
    return;
  }

  const scrapeBtn = document.getElementById("scrape-btn");
  const detailsBtn = document.getElementById("scrape-with-details");
  scrapeBtn.disabled = true;
  detailsBtn.disabled = true;

  hideResults();
  showStatus("🔄 Sending request to scraping service...", "loading");

  const requestData = {
    url: url,
    strategy: "HYBRID",
    forceRefresh: true,
    maxProducts: withDetails ? 50 : 25,
  };

  if (withDetails) {
    requestData.requiredFields = [
      "name",
      "price",
      "image",
      "description",
      "url",
      "inStock",
    ];
  }

  // Add timeout to the fetch request
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

  fetch("http://localhost:8080/api/scraping/products", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestData),
    signal: controller.signal,
  })
    .then((response) => {
      clearTimeout(timeoutId);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        currentResults = data;
        displayAllResults(data, url);
      } else {
        showStatus(`❌ Error: ${data.message}`, "error");
      }
    })
    .catch((error) => {
      clearTimeout(timeoutId);
      console.error("Error:", error);

      let errorMessage = "❌ ";
      if (error.name === "AbortError") {
        errorMessage +=
          "Request timed out. The scraping service is taking too long to respond.";
      } else if (error.message.includes("Failed to fetch")) {
        errorMessage +=
          "Cannot connect to scraping service. Make sure your Spring Boot server is running on localhost:8080";
      } else {
        errorMessage += error.message;
      }

      showStatus(errorMessage, "error");
    })
    .finally(() => {
      setTimeout(() => {
        scrapeBtn.disabled = false;
        detailsBtn.disabled = false;
      }, 2000);
    });
}

// Helper functions (keep these the same)
function resolveImageUrl(imageUrl, baseUrl) {
  if (!imageUrl || imageUrl === "null" || imageUrl === "") return null;

  if (imageUrl.startsWith("http")) {
    return imageUrl;
  }

  if (imageUrl.startsWith("//")) {
    return "https:" + imageUrl;
  }

  try {
    const base = new URL(baseUrl);
    return new URL(imageUrl, base).href;
  } catch (e) {
    console.warn("Failed to resolve image URL:", imageUrl, e);
    return null;
  }
}

function resolveProductUrl(productUrl, baseUrl) {
  if (!productUrl || productUrl === "null" || productUrl === "") return null;

  if (productUrl.startsWith("http")) {
    return productUrl;
  }

  if (productUrl.startsWith("//")) {
    return "https:" + productUrl;
  }

  try {
    const base = new URL(baseUrl);
    return new URL(productUrl, base).href;
  } catch (e) {
    console.warn("Failed to resolve product URL:", productUrl, e);
    return null;
  }
}

function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

function createProductElement(product, index, baseUrl) {
  const productDiv = document.createElement("div");
  productDiv.className = "product-item";

  const resolvedImageUrl = resolveImageUrl(product.imageUrl, baseUrl);
  const resolvedProductUrl = resolveProductUrl(product.url, baseUrl);
  const hasImage = resolvedImageUrl !== null;

  const stockStatus = product.inStock ? "in-stock" : "out-of-stock";
  const stockText = product.inStock ? "✅ In Stock" : "❌ Out of Stock";

  productDiv.innerHTML = `
    <div class="product-name">${index}. ${product.name || "No name available"}</div>
    <div class="product-details">
      <div class="product-price">💰 ${product.price || "Price not available"}</div>
      <div class="product-stock ${stockStatus}">${stockText}</div>
    </div>
    ${product.description ? `<div style="font-size: 11px; color: #6c757d; margin-top: 5px; line-height: 1.3;">${truncateText(product.description, 100)}</div>` : ""}
    <div class="product-image ${!hasImage ? "no-image" : ""}">
      ${
        hasImage
          ? `<img src="${resolvedImageUrl}" alt="${product.name || "Product image"}" onerror="handleImageError(this)" />`
          : "🖼️ No image available"
      }
    </div>
    ${resolvedProductUrl ? `<div style="font-size: 10px; color: #007bff; margin-top: 5px; word-break: break-all;"><a href="${resolvedProductUrl}" target="_blank" style="color: inherit;">🔗 View Product Page</a></div>` : ""}
  `;

  return productDiv;
}

function handleImageError(imgElement) {
  const container = imgElement.parentElement;
  container.classList.add("no-image");
  container.innerHTML = "🖼️ Image failed to load";
  console.warn("Image failed to load:", imgElement.src);
}

function truncateText(text, maxLength) {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}

function displayAllResults(data, baseUrl) {
  const productCount = data.data?.productCount || 0;
  const platform = data.data?.platform || "Unknown";
  const products = data.data?.products || [];

  if (productCount === 0) {
    showStatus("❌ No products found on this page.", "error");
    return;
  }

  document.getElementById("results-count").textContent =
    `📦 ${productCount} products found (${platform})`;

  const productsContainer = document.getElementById("products-container");
  productsContainer.innerHTML = "";

  // Use requestAnimationFrame for smoother rendering of many products
  requestAnimationFrame(() => {
    products.forEach((product, index) => {
      const productElement = createProductElement(product, index + 1, baseUrl);
      productsContainer.appendChild(productElement);
    });
  });

  showResults();
  console.log("🎯 Full scraping results:", data);
}

function showResults() {
  document.getElementById("status").classList.add("hidden");
  document.getElementById("results-section").classList.remove("hidden");
}

function hideResults() {
  document.getElementById("results-section").classList.add("hidden");
}

function showStatus(message, type) {
  const statusDiv = document.getElementById("status");
  statusDiv.textContent = message;
  statusDiv.className = `status-message ${type}`;
  statusDiv.classList.remove("hidden");

  hideResults();
}

function copyResultsToClipboard() {
  if (!currentResults) return;

  const resultsText = JSON.stringify(currentResults, null, 2);

  navigator.clipboard
    .writeText(resultsText)
    .then(() => {
      const originalText = document.getElementById("copy-json").textContent;
      document.getElementById("copy-json").textContent = "✅ Copied!";

      setTimeout(() => {
        document.getElementById("copy-json").textContent = originalText;
      }, 2000);
    })
    .catch((err) => {
      console.error("Failed to copy: ", err);
      alert("Failed to copy results to clipboard");
    });
}

function viewResultsInConsole() {
  if (!currentResults) return;

  console.log("🛍️ Full scraping results:", currentResults);
  const products = currentResults.data?.products || [];

  console.log("📦 All products:");
  products.forEach((product, index) => {
    console.log(`%c${index + 1}. ${product.name}`, "font-weight: bold");
    console.log(`   Price: ${product.price}`);
    console.log(
      `   Stock: ${product.inStock ? "✅ In Stock" : "❌ Out of Stock"}`,
    );
    console.log(`   Image: ${product.imageUrl || "No image"}`);
    console.log(`   URL: ${product.url || "No URL"}`);
    console.log("---");
  });

  alert(
    `Check the browser console (F12) for all ${products.length} products with full details!`,
  );
}

// Keyboard shortcuts
document.addEventListener("keydown", function (e) {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === "1") {
      document.getElementById("scrape-btn").click();
    } else if (e.key === "2") {
      document.getElementById("scrape-with-details").click();
    }
  }
});
