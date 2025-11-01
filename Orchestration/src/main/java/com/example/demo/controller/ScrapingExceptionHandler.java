package com.example.demo.controller;

import com.example.demo.exception.*;
import com.example.demo.model.ErrorResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ControllerAdvice;

@ControllerAdvice
public class ScrapingExceptionHandler {
    
    @ExceptionHandler(ScrapingTimeoutException.class)
    public ResponseEntity<ErrorResponse> handleTimeout(ScrapingTimeoutException ex) {
        return ResponseEntity.status(HttpStatus.REQUEST_TIMEOUT)
                .body(ErrorResponse.timeout(ex.getMessage()));
    }
    
    @ExceptionHandler(SelectorDiscoveryException.class)
    public ResponseEntity<ErrorResponse> handleSelectorDiscovery(SelectorDiscoveryException ex) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
                .body(ErrorResponse.selectorError(ex.getMessage()));
    }
    
    @ExceptionHandler(CacheException.class)
    public ResponseEntity<ErrorResponse> handleCacheException(CacheException ex) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ErrorResponse.cacheError(ex.getMessage()));
    }
    
    @ExceptionHandler(ScrapingExecutionException.class)
    public ResponseEntity<ErrorResponse> handleScrapingExecution(ScrapingExecutionException ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorResponse.scrapingError(ex.getMessage()));
    }
    
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorResponse.genericError("An unexpected error occurred"));
    }
}