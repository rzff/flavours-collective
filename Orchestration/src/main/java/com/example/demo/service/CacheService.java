package com.example.demo.service;

import com.example.demo.models.*;
import org.springframework.stereotype.Service;

@Service
public class CacheService {
    
    public CacheResult checkDomainCache(String url) {
        CacheResult result = new CacheResult();
        result.setHit(false);
        result.setValid(true);
        return result;
    }
    
    public CacheInfo getCacheInfo(String domain) {
        return new CacheInfo();
    }
}