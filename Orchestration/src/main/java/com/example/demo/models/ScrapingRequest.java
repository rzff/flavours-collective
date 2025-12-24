package com.example.demo.models;

import jakarta.validation.constraints.NotBlank;
import org.hibernate.validator.constraints.URL;

public class ScrapingRequest {
    
    @NotBlank(message = "URL is required")
    @URL(message = "Must be a valid URL")
    private String url;

    // Add this field to fix the compilation error
    private Integer maxProducts;

    public ScrapingRequest() {}

    public ScrapingRequest(String url) {
        this.url = url;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    // Add these methods
    public Integer getMaxProducts() {
        return maxProducts;
    }

    public void setMaxProducts(Integer maxProducts) {
        this.maxProducts = maxProducts;
    }
}