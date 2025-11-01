package com.example.demo.service;

import com.example.demo.model.*;
import com.example.demo.exception.ScrapingExecutionException;
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
            // Call the Python service's single scrape endpoint
            ScrapeResponse pythonResponse = pythonService.callScrape(url);
            
            // Convert Python response to Spring Boot format
            ScrapingResult result = convertToScrapingResult(pythonResponse);
            result.setProcessingTime(System.currentTimeMillis() - startTime);
            result.setCacheStatus(cacheResult.isHit() ? "HIT" : "MISS");
            
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
        
        // Convert Python products to Spring Boot products
        if (pythonResponse.getProducts() != null) {
            result.setProducts(pythonResponse.getProducts().stream()
                .map(this::convertProduct)
                .toList());
        }
        
        result.setProductCount(result.getProducts() != null ? result.getProducts().size() : 0);
        return result;
    }
    
    private Product convertProduct(com.example.demo.model.Product pythonProduct) {
        Product product = new Product();
        product.setName(pythonProduct.getName());
        product.setUrl(pythonProduct.getUrl());
        product.setPrice(pythonProduct.getPrice());
        product.setImageUrl(pythonProduct.getImageUrl());
        product.setDescription(pythonProduct.getDescription());
        product.setInStock(pythonProduct.getInStock());
        return product;
    }
}