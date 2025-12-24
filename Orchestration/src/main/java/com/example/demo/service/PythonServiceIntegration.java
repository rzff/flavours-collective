package com.example.demo.service;

import com.example.demo.models.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import java.util.Map;

@Component
public class PythonServiceIntegration {
    
    private final RestTemplate restTemplate;
    private final String pythonBaseUrl;
    
    @Autowired
    public PythonServiceIntegration(RestTemplate restTemplate,
                                  @Value("${python.service.base-url:http://localhost:8000}") String pythonBaseUrl) {
        this.restTemplate = restTemplate;
        this.pythonBaseUrl = pythonBaseUrl;
    }
    
    // Your Python service has a single /scrape endpoint that does everything
    public ScrapeResponse callScrape(String url) {
        try {
            return restTemplate.postForObject(
                pythonBaseUrl + "/scrape",
                Map.of("url", url),
                ScrapeResponse.class
            );
        } catch (Exception e) {
            throw new RuntimeException("Failed to call Python scrape service: " + e.getMessage(), e);
        }
    }
}