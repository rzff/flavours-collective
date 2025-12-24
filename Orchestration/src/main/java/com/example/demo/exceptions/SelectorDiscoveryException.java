package com.example.demo.exceptions;

public class SelectorDiscoveryException extends RuntimeException {
    public SelectorDiscoveryException(String message) {
        super(message);
    }
    
    public SelectorDiscoveryException(String message, Throwable cause) {
        super(message, cause);
    }
}