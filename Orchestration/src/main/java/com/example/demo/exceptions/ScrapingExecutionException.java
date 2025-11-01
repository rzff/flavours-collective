package com.example.demo.exception;

public class ScrapingExecutionException extends RuntimeException {
    public ScrapingExecutionException(String message) {
        super(message);
    }
    
    public ScrapingExecutionException(String message, Throwable cause) {
        super(message, cause);
    }
}