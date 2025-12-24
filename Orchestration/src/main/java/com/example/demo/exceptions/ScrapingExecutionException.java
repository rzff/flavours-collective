package com.example.demo.exceptions;

public class ScrapingExecutionException extends RuntimeException {
    public ScrapingExecutionException(String message) {
        super(message);
    }
    
    public ScrapingExecutionException(String message, Throwable cause) {
        super(message, cause);
    }
}