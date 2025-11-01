package com.example.demo.controller;

import com.example.demo.service.ScrapingOrchestrationService;
import com.example.demo.service.CacheService;
import com.example.demo.service.PerformanceMonitor;
import com.example.demo.model.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/scraping")
public class ScrapingController {
    
    private final ScrapingOrchestrationService scrapingOrchestrationService;
    private final CacheService cacheService;
    private final PerformanceMonitor performanceMonitor;
    
    @Autowired
    public ScrapingController(ScrapingOrchestrationService scrapingOrchestrationService,
                            CacheService cacheService,
                            PerformanceMonitor performanceMonitor) {
        this.scrapingOrchestrationService = scrapingOrchestrationService;
        this.cacheService = cacheService;
        this.performanceMonitor = performanceMonitor;
    }
    
    @PostMapping("/products")
    public ResponseEntity<ScrapingResponse> scrapeProducts(@Valid @RequestBody ScrapingRequest request) {
        long startTime = System.currentTimeMillis();
        
        try {
            ScrapingResult result = scrapingOrchestrationService.scrapeProducts(
                request.getUrl(), 
                request
            );
            
            performanceMonitor.recordScrapingMetrics(
                extractDomain(request.getUrl()), 
                result.getCacheStatus(), 
                System.currentTimeMillis() - startTime
            );
            
            return ResponseEntity.ok(ScrapingResponse.from(result));
            
        } catch (Exception e) {
            performanceMonitor.recordScrapingError(extractDomain(request.getUrl()));
            return ResponseEntity.internalServerError()
                    .body(ScrapingResponse.error("Scraping failed: " + e.getMessage()));
        }
    }
    
    @GetMapping("/cache/domain/{domain}")
    public ResponseEntity<CacheInfo> getCacheInfo(@PathVariable String domain) {
        try {
            CacheInfo cacheInfo = cacheService.getCacheInfo(domain);
            return ResponseEntity.ok(cacheInfo);
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }
    
    @DeleteMapping("/cache/domain/{domain}")
    public ResponseEntity<Void> clearDomainCache(@PathVariable String domain) {
        cacheService.invalidateCache(domain);
        return ResponseEntity.ok().build();
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