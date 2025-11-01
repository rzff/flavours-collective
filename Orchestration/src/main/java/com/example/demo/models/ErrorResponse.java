package com.example.demo.model;

import lombok.Data;
import lombok.Builder;
import java.time.LocalDateTime;

@Data
@Builder
public class ErrorResponse {
    private String error;
    private String message;
    private LocalDateTime timestamp;
    private String errorType;
    
    public static ErrorResponse timeout(String message) {
        return ErrorResponse.builder()
                .error("Scraping Timeout")
                .message(message)
                .timestamp(LocalDateTime.now())
                .errorType("TIMEOUT")
                .build();
    }
    
    public static ErrorResponse selectorError(String message) {
        return ErrorResponse.builder()
                .error("Selector Discovery Failed")
                .message(message)
                .timestamp(LocalDateTime.now())
                .errorType("SELECTOR_DISCOVERY")
                .build();
    }
    
    public static ErrorResponse cacheError(String message) {
        return ErrorResponse.builder()
                .error("Cache Service Error")
                .message(message)
                .timestamp(LocalDateTime.now())
                .errorType("CACHE_ERROR")
                .build();
    }
    
    public static ErrorResponse scrapingError(String message) {
        return ErrorResponse.builder()
                .error("Scraping Execution Failed")
                .message(message)
                .timestamp(LocalDateTime.now())
                .errorType("SCRAPING_ERROR")
                .build();
    }
    
    public static ErrorResponse genericError(String message) {
        return ErrorResponse.builder()
                .error("Internal Server Error")
                .message(message)
                .timestamp(LocalDateTime.now())
                .errorType("GENERIC_ERROR")
                .build();
    }
}