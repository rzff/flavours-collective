package com.example.demo.models;

import java.util.List;
import java.util.Map;

public class ScrapeResponse {
    private String url;
    private String platform;
    private String pageType;
    private String selector;
    private Map<String, List<String>> fieldSelectors;
    private List<Product> products;
    private String cacheStatus;
    
    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
    
    public String getPlatform() { return platform; }
    public void setPlatform(String platform) { this.platform = platform; }
    
    public String getPageType() { return pageType; }
    public void setPageType(String pageType) { this.pageType = pageType; }
    
    public String getSelector() { return selector; }
    public void setSelector(String selector) { this.selector = selector; }
    
    public Map<String, List<String>> getFieldSelectors() { return fieldSelectors; }
    public void setFieldSelectors(Map<String, List<String>> fieldSelectors) { 
        this.fieldSelectors = fieldSelectors; 
    }
    
    public List<Product> getProducts() { return products; }
    public void setProducts(List<Product> products) { this.products = products; }
    
    public String getCacheStatus() { return cacheStatus; }
    public void setCacheStatus(String cacheStatus) { this.cacheStatus = cacheStatus; }
}
