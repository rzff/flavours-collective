package com.example.demo.model;

import lombok.Data;

@Data
public class PlatformAnalysis {
    private String platform;
    private Double confidence;
    private String platformType; // SHOPIFY, WOOCOMMERCE, CUSTOM
    private Boolean requiresJavaScript;
    private String detectionMethod;
}