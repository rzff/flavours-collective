package com.example.demo.controller;

import com.example.demo.models.ScrapingRequest;
import com.example.demo.models.ScrapingResult;
import com.example.demo.service.ScrapingOrchestrationService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/scraping")
@CrossOrigin(origins = "*") // CRITICAL: This allows the Chrome Extension to talk to Java
public class ScrapingController {

    private final ScrapingOrchestrationService scrapingService;

    public ScrapingController(ScrapingOrchestrationService scrapingService) {
        this.scrapingService = scrapingService;
    }

    @PostMapping("/products")
    public ScrapingResult scrapeProducts(@RequestBody ScrapingRequest request) {
        return scrapingService.scrapeProducts(request.getUrl(), request);
    }

    @PostMapping("/store")
    public ScrapingResult storeProducts(@RequestBody ScrapingResult results) {
        return scrapingService.saveScrapedResults(results);
    }
}