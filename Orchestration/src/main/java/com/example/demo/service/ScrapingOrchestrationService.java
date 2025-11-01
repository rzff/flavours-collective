package com.example.demo.service;

import com.example.demo.model.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class ScrapingOrchestrationService {
    
    private final CacheService cacheService;
    private final AgentCoordinator agentCoordinator;
    private final PerformanceMonitor performanceMonitor;
    
    @Autowired
    public ScrapingOrchestrationService(CacheService cacheService,
                                      AgentCoordinator agentCoordinator,
                                      PerformanceMonitor performanceMonitor) {
        this.cacheService = cacheService;
        this.agentCoordinator = agentCoordinator;
        this.performanceMonitor = performanceMonitor;
    }
    
    public ScrapingResult scrapeProducts(String url, ScrapingRequest request) {
        // 1. Check cache first
        CacheResult cacheResult = cacheService.checkDomainCache(url);
        
        if (cacheResult.isHit() && cacheResult.isValid() && !request.isForceRefresh()) {
            return buildResponseFromCache(cacheResult);
        }
        
        // 2. Orchestrate agent workflow
        return agentCoordinator.executeScrapingWorkflow(url, request, cacheResult);
    }
    
    private ScrapingResult buildResponseFromCache(CacheResult cacheResult) {
        ScrapingResult result = new ScrapingResult();
        result.setUrl(cacheResult.getSelectorInfo().getMainSelector());
        result.setPlatform(cacheResult.getSelectorInfo().getPlatform());
        result.setPageType(cacheResult.getSelectorInfo().getPageType());
        result.setSelector(cacheResult.getSelectorInfo().getMainSelector());
        result.setFieldSelectors(cacheResult.getSelectorInfo().getFieldSelectors());
        result.setCacheStatus("HIT");
        return result;
    }
}