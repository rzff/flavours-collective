package com.example.demo.service;

import com.example.demo.models.*;
import com.example.demo.repository.ProductRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import java.util.Map;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ScrapingOrchestrationService {

    // 1. DO NOT use "= new RestTemplate()" here. Leave it blank.
    private final RestTemplate restTemplate;
    private final ProductRepository productRepository; 
    private final String FASTAPI_URL = "http://127.0.0.1:8000/scrape";

    // 2. Spring will now inject your custom Config (the 120s timeout) into this constructor
    public ScrapingOrchestrationService(ProductRepository productRepository, RestTemplate restTemplate) {
        this.productRepository = productRepository;
        this.restTemplate = restTemplate;
    }

    @Transactional
    public ScrapingResult scrapeProducts(String url, ScrapingRequest request) {
        Map<String, String> payload = Map.of("url", url);
        
        try {
            // 3. This call will now wait for 120 seconds instead of 7.
            ScrapingResult result = restTemplate.postForObject(FASTAPI_URL, payload, ScrapingResult.class);
            
            if (result != null && result.getProducts() != null) {
                List<ProductEntity> entities = result.getProducts().stream()
                    .map(ProductEntity::fromProduct)
                    .collect(Collectors.toList());
                
                productRepository.saveAll(entities);
            }
            
            return result;
        } catch (Exception e) {
            // Log the error so you can see exactly why it failed
            System.err.println("Error during FastAPI call: " + e.getMessage());
            throw new RuntimeException("FastAPI Connection Failed: " + e.getMessage());
        }
    }
}