package com.example.demo.service;

import com.example.demo.model.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

@Service
public class CacheService {
    
    @Cacheable(value = "domainSelectors", key = "#url")
    public CacheResult checkDomainCache(String url) {
        // Since Python service handles its own cache, we'll just track misses
        CacheResult miss = new CacheResult();
        miss.setHit(false);
        miss.setValid(false);
        miss.setDomain(extractDomain(url));
        return miss;
    }
    
    @CacheEvict(value = "domainSelectors", key = "#domain")
    public void invalidateCache(String domain) {
        // Cache invalidation is handled by Python service
        System.out.println("Cache invalidation requested for domain: " + domain);
    }
    
    public CacheInfo getCacheInfo(String domain) {
        // Return basic cache info
        CacheInfo info = new CacheInfo();
        info.setDomain(domain);
        info.setIsValid(false);
        return info;
    }
    
    private String extractDomain(String url) {
        try {
            java.net.URI uri = new java.net.URI(url);
            return uri.getHost();
        } catch (Exception e) {
            return "unknown";
        }
    }
}