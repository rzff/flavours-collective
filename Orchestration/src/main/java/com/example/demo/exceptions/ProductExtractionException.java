package com.example.demo.exception;

public class ProductExtractionException extends RuntimeException {
    public ProductExtractionException(String message) {
        super(message);
    }
    
    public ProductExtractionException(String message, Throwable cause) {
        super(message, cause);
    }
}