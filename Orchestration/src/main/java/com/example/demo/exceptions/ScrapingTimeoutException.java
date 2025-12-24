package com.example.demo.exceptions;

public class ScrapingTimeoutException extends RuntimeException {
    public ScrapingTimeoutException(String message) {
        super(message);
    }
    
    public ScrapingTimeoutException(String message, Throwable cause) {
        super(message, cause);
    }
}