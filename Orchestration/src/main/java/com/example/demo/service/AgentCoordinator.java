package com.example.demo.service;

import com.example.demo.models.*;
import com.example.demo.exceptions.ScrapingExecutionException; // Changed to exceptions (plural)
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class AgentCoordinator {
    
    @Autowired
    private PythonServiceIntegration pythonService;
    
    @Autowired
    private CacheService cacheService;
    
    public ScrapingResult executeScrapingWorkflow(String url, ScrapingRequest config, CacheResult cacheResult) {
        long startTime = System.currentTimeMillis();
        
        try {
            ScrapeResponse pythonResponse = pythonService.callScrape(url);
            
            ScrapingResult result = convertToScrapingResult(pythonResponse);
            result.setProcessingTime(System.currentTimeMillis() - startTime);
            result.setCacheStatus(cacheResult.isHit() ? "HIT" : "MISS");
            
            System.out.println("AgentCoordinator executed for: " + url);
            
            return result;
            
        } catch (Exception e) {
            throw new ScrapingExecutionException("Failed to execute scraping workflow for URL: " + url, e);
        }
    }
    
    private ScrapingResult convertToScrapingResult(ScrapeResponse pythonResponse) {
        ScrapingResult result = new ScrapingResult();
        result.setUrl(pythonResponse.getUrl());
        result.setPlatform(pythonResponse.getPlatform());
        result.setPageType(pythonResponse.getPageType());
        result.setSelector(pythonResponse.getSelector());
        result.setFieldSelectors(pythonResponse.getFieldSelectors());
        result.setProducts(pythonResponse.getProducts());
        
        if (result.getProducts() != null) {
            result.setProductCount(result.getProducts().size());
        } else {
            result.setProductCount(0);
        }
        
        return result;
    }
}