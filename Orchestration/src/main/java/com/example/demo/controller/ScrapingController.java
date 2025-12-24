package com.example.demo.controller;

import com.example.demo.models.ScrapingRequest;
import com.example.demo.models.ScrapingResult;
import com.example.demo.service.ScrapingOrchestrationService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/scraping")
public class ScrapingController {

    private final ScrapingOrchestrationService scrapingService;

    // Inject the service
    public ScrapingController(ScrapingOrchestrationService scrapingService) {
        this.scrapingService = scrapingService;
    }

    @PostMapping("/products")
    public ScrapingResult scrapeProducts(@RequestBody ScrapingRequest request) {
        // THIS LINE IS CRITICAL: It must call the service!
        return scrapingService.scrapeProducts(request.getUrl(), request);
    }
}