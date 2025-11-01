package com.example.demo.model;

import lombok.Data;
import jakarta.validation.constraints.NotBlank;
import java.util.Set;

@Data
public class ScrapingRequest {
    @NotBlank(message = "URL is required")
    private String url;
    
    private ScrapingStrategy strategy; // STATIC_FIRST, PLAYWRIGHT_FIRST, HYBRID
    private boolean forceRefresh;
    private Integer maxProducts;
    private Set<String> requiredFields;
}