package com.example.demo.service;

import com.example.demo.models.*;
import com.example.demo.repository.ProductRepository;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value; // Add this import
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

@Service
public class ScrapingOrchestrationService {

    private final RestTemplate restTemplate;
    private final ProductRepository productRepository;

    // This reads the env var from Docker Compose.
    // If it's missing, it defaults to localhost for local dev.
    @Value("${SCRAPER_URL:http://127.0.0.1:8000}")
    private String scraperBaseUrl;

    public ScrapingOrchestrationService(
        ProductRepository productRepository,
        RestTemplate restTemplate
    ) {
        this.productRepository = productRepository;
        this.restTemplate = restTemplate;
    }

    @Transactional
    public ScrapingResult scrapeProducts(String url, ScrapingRequest request) {
        Map<String, String> payload = Map.of("url", url);

        // Build the full URL dynamically
        String fullUrl = scraperBaseUrl + "/scrape";

        try {
            System.out.println("Attempting to call Scraper at: " + fullUrl); // Useful for logging

            ScrapingResult result = restTemplate.postForObject(
                fullUrl,
                payload,
                ScrapingResult.class
            );

            if (result != null && result.getProducts() != null) {
                List<ProductEntity> entities = result
                    .getProducts()
                    .stream()
                    .map(ProductEntity::fromProduct)
                    .collect(Collectors.toList());

                productRepository.saveAll(entities);
            }

            return result;
        } catch (Exception e) {
            System.err.println(
                "Error during FastAPI call to " +
                    fullUrl +
                    ": " +
                    e.getMessage()
            );
            throw new RuntimeException(
                "FastAPI Connection Failed: " + e.getMessage()
            );
        }
    }



@Transactional
public ScrapingResult saveScrapedResults(ScrapingResult results) {
    System.out.println("Storing " + results.getData().getProductCount() + " products from " + results.getData().getPlatform());

    try {
        List<ProductEntity> entities = results.getData().getProducts().stream()
            .map(ProductEntity::fromProduct)
            .collect(Collectors.toList());

        System.out.println("Mapped to " + entities.size() + " entities. Committing to DB...");
        
        // This is the critical line:
        List<ProductEntity> saved = productRepository.saveAll(entities);
        
        System.out.println("Successfully saved " + saved.size() + " items to the database.");
        results.setSuccess(true);
    } catch (Exception e) {
        System.err.println("DB SAVE ERROR: " + e.getMessage());
        e.printStackTrace(); // This will show up in your Docker logs if it fails
        results.setSuccess(false);
    }

    return results;
}
}
