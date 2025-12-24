package com.example.demo.models;

import java.util.List;
import java.util.Map;

public class SelectorInfo {
    private String selector;
    private String mainSelector;
    private String platform;
    private String pageType;
    private Map<String, List<String>> fieldSelectors;
    
    public String getSelector() { return selector; }
    public void setSelector(String selector) { this.selector = selector; }
    
    public String getMainSelector() { return mainSelector; }
    public void setMainSelector(String mainSelector) { this.mainSelector = mainSelector; }
    
    public String getPlatform() { return platform; }
    public void setPlatform(String platform) { this.platform = platform; }
    
    public String getPageType() { return pageType; }
    public void setPageType(String pageType) { this.pageType = pageType; }
    
    public Map<String, List<String>> getFieldSelectors() { return fieldSelectors; }
    public void setFieldSelectors(Map<String, List<String>> fieldSelectors) { 
        this.fieldSelectors = fieldSelectors; 
    }
}
