package com.example.demo.model;

import lombok.Data;

@Data
public class CacheResult {
    private boolean hit;
    private boolean valid;
    private String domain;
    private SelectorInfo selectorInfo;
    private Long timestamp;
    private String cacheKey;
    
    public boolean isValid() {
        return valid && selectorInfo != null;
    }
}