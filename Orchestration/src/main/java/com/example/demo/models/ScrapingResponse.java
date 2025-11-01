package com.example.demo.model;

import lombok.Data;
import lombok.Builder;

@Data
@Builder
public class ScrapingResponse {
    private boolean success;
    private String message;
    private ScrapingResult data;
    private Long timestamp;
    
    public static ScrapingResponse from(ScrapingResult result) {
        return ScrapingResponse.builder()
                .success(true)
                .message("Scraping completed successfully")
                .data(result)
                .timestamp(System.currentTimeMillis())
                .build();
    }
    
    public static ScrapingResponse error(String message) {
        return ScrapingResponse.builder()
                .success(false)
                .message(message)
                .timestamp(System.currentTimeMillis())
                .build();
    }
}