package com.example.demo.model;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class ScrapingResult {
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
}