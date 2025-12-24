package com.example.demo.controller;

import com.example.demo.models.ErrorResponse;
import com.example.demo.exceptions.*; // Changed to exceptions
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ScrapingExceptionHandler {
    
    @ExceptionHandler(ScrapingTimeoutException.class)
    public ResponseEntity<ErrorResponse> handleTimeout(ScrapingTimeoutException ex) {
        ErrorResponse error = ErrorResponse.timeout(ex.getMessage());
        return ResponseEntity.status(HttpStatus.REQUEST_TIMEOUT).body(error);
    }
    
    @ExceptionHandler(SelectorDiscoveryException.class)
    public ResponseEntity<ErrorResponse> handleSelectorDiscovery(SelectorDiscoveryException ex) {
        ErrorResponse error = ErrorResponse.selectorDiscovery(ex.getMessage());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }
    
    @ExceptionHandler(CacheException.class)
    public ResponseEntity<ErrorResponse> handleCacheException(CacheException ex) {
        ErrorResponse error = ErrorResponse.cacheError(ex.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
    
    @ExceptionHandler(ScrapingExecutionException.class)
    public ResponseEntity<ErrorResponse> handleScrapingExecution(ScrapingExecutionException ex) {
        ErrorResponse error = ErrorResponse.scrapingExecution(ex.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
    
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(Exception ex) {
        ErrorResponse error = ErrorResponse.generic(ex.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}