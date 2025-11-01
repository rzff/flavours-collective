package com.example.demo.model;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class CacheInfo {
    private String domain;
    private String cacheKey;
    private LocalDateTime lastUpdated;
    private Integer hitCount;
    private SelectorInfo selectorInfo;
    private Boolean isValid;
}