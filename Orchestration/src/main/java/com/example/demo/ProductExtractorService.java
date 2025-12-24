package com.example.demo;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.beans.factory.annotation.Value;
import com.example.demo.models.*;
import com.example.demo.exceptions.ProductExtractionException; // Changed to exceptions
import java.util.List;
import java.util.Map;

@Service
public class ProductExtractorService {
    
    private final RestTemplate restTemplate;
    
    @Value("${python.service.base-url:http://localhost:8000}")
    private String pythonServiceUrl;
    
    public ProductExtractorService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }
    
    public List<Product> extractProducts(String url, SelectorInfo selectors, 
                                       PageType pageType, ScrapingRequest config) {
        try {
            var requestBody = Map.of(
                "url", url,
                "selectors", selectors,
                "pageType", pageType.name(),
                "maxProducts", config.getMaxProducts() != null ? config.getMaxProducts() : 50
            );
            
            var response = restTemplate.postForEntity(
                pythonServiceUrl + "/extract-products",
                requestBody,
                Product[].class
            );
            
            return List.of(response.getBody());
        } catch (Exception e) {
            throw new ProductExtractionException("Failed to extract products from URL: " + url, e);
        }
    }
}