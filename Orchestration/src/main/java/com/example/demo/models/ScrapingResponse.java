package com.example.demo.models;

public class ScrapingResponse {
    private boolean success;
    private String message;
    private ScrapingResult data;
    private Long processingTime;
    
    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }
    
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    
    public ScrapingResult getData() { return data; }
    public void setData(ScrapingResult data) { this.data = data; }
    
    public Long getProcessingTime() { return processingTime; }
    public void setProcessingTime(Long processingTime) { this.processingTime = processingTime; }
    
    public static ScrapingResponse from(ScrapingResult result) {
        ScrapingResponse response = new ScrapingResponse();
        response.setSuccess(true);
        response.setData(result);
        return response;
    }
    
    public static ScrapingResponse error(String message) {
        ScrapingResponse response = new ScrapingResponse();
        response.setSuccess(false);
        response.setMessage(message);
        return response;
    }
}