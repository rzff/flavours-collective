package com.example.demo.models;

import lombok.Data;
import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Entity
@Table(name = "scrape_responses")
public class ScrapeResponseEntity {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false, length = 2048)
    private String url;
    
    private String platform;
    
    @Column(name = "page_type")
    private String pageType;
    
    private String selector;
    
    @ElementCollection
    @CollectionTable(name = "scrape_response_field_selectors", 
                     joinColumns = @JoinColumn(name = "scrape_response_id"))
    @MapKeyColumn(name = "field_name")
    @Column(name = "selector_value", columnDefinition = "TEXT")
    private Map<String, List<String>> fieldSelectors;
    
    @OneToMany(cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    @JoinColumn(name = "scrape_response_id")
    private List<ProductEntity> products;
    
    @Column(name = "cache_status")
    private String cacheStatus;
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
    
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}