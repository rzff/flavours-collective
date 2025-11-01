package com.example.demo.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.concurrent.TimeUnit;

@Component
public class PerformanceMonitor {
    
    private final MeterRegistry meterRegistry;
    private final Counter cacheHits;
    private final Counter cacheMisses;
    private final Counter scrapingErrors;
    private final Timer scrapingTimer;
    
    @Autowired
    public PerformanceMonitor(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
        this.cacheHits = Counter.builder("scraping.cache.hits")
                .description("Number of cache hits")
                .register(meterRegistry);
        this.cacheMisses = Counter.builder("scraping.cache.misses")
                .description("Number of cache misses")
                .register(meterRegistry);
        this.scrapingErrors = Counter.builder("scraping.errors")
                .description("Number of scraping errors")
                .register(meterRegistry);
        this.scrapingTimer = Timer.builder("scraping.duration")
                .description("Time taken for scraping operations")
                .register(meterRegistry);
    }
    
    public void recordScrapingMetrics(String domain, String cacheStatus, long duration) {
        scrapingTimer.record(duration, TimeUnit.MILLISECONDS);
        
        if ("HIT".equals(cacheStatus)) {
            cacheHits.increment();
        } else {
            cacheMisses.increment();
        }
        
        // Domain-specific metrics
        meterRegistry.counter("scraping.requests", "domain", domain).increment();
    }
    
    public void recordScrapingError(String domain) {
        scrapingErrors.increment();
        meterRegistry.counter("scraping.errors", "domain", domain).increment();
    }
}