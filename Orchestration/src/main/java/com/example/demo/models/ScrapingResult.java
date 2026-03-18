package com.example.demo.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ScrapingResult {
    // --- Fields for Browser Extension Flow ---
    private boolean success;
    private ScrapedData data; // This contains the platform and product list from the extension

    // --- Original Fields for FastAPI Flow ---
    private String url;
    private String platform;
    private String pageType;
    private String selector;
    private Map<String, List<String>> fieldSelectors;
    private List<Product> products;
    private String cacheStatus;
    private Long processingTime;
    private Integer productCount;
    private String errorMessage;

    // --- New Getters/Setters for Extension Flow ---
    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }

    public ScrapedData getData() { return data; }
    public void setData(ScrapedData data) { this.data = data; }

    // --- Existing Getters/Setters ---
    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
    
    public String getPlatform() { return platform; }
    public void setPlatform(String platform) { this.platform = platform; }
    
    public String getPageType() { return pageType; }
    public void setPageType(String pageType) { this.pageType = pageType; }
    
    public String getSelector() { return selector; }
    public void setSelector(String selector) { this.selector = selector; }
    
    public Map<String, List<String>> getFieldSelectors() { return fieldSelectors; }
    public void setFieldSelectors(Map<String, List<String>> fieldSelectors) { this.fieldSelectors = fieldSelectors; }
    
    public List<Product> getProducts() { return products; }
    public void setProducts(List<Product> products) { this.products = products; }
    
    public String getCacheStatus() { return cacheStatus; }
    public void setCacheStatus(String cacheStatus) { this.cacheStatus = cacheStatus; }
    
    public Long getProcessingTime() { return processingTime; }
    public void setProcessingTime(Long processingTime) { this.processingTime = processingTime; }
    
    public Integer getProductCount() { return productCount; }
    public void setProductCount(Integer productCount) { this.productCount = productCount; }
    
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
}