package com.example.demo.exception;

public class ScrapingTimeoutException extends RuntimeException {
    public ScrapingTimeoutException(String message) {
        super(message);
    }
}