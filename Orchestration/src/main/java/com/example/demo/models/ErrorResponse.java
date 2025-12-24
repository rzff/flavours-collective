package com.example.demo.models;

public class ErrorResponse {
    private String error;
    private String message;
    private long timestamp;
    
    public String getError() { return error; }
    public void setError(String error) { this.error = error; }
    
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    
    public static ErrorResponse timeout(String message) {
        ErrorResponse response = new ErrorResponse();
        response.setError("Scraping Timeout");
        response.setMessage(message);
        response.setTimestamp(System.currentTimeMillis());
        return response;
    }
    
    public static ErrorResponse selectorDiscovery(String message) {
        ErrorResponse response = new ErrorResponse();
        response.setError("Selector Discovery Failed");
        response.setMessage(message);
        response.setTimestamp(System.currentTimeMillis());
        return response;
    }
    
    public static ErrorResponse cacheError(String message) {
        ErrorResponse response = new ErrorResponse();
        response.setError("Cache Error");
        response.setMessage(message);
        response.setTimestamp(System.currentTimeMillis());
        return response;
    }
    
    public static ErrorResponse scrapingExecution(String message) {
        ErrorResponse response = new ErrorResponse();
        response.setError("Scraping Execution Failed");
        response.setMessage(message);
        response.setTimestamp(System.currentTimeMillis());
        return response;
    }
    
    public static ErrorResponse generic(String message) {
        ErrorResponse response = new ErrorResponse();
        response.setError("Internal Server Error");
        response.setMessage(message);
        response.setTimestamp(System.currentTimeMillis());
        return response;
    }
}