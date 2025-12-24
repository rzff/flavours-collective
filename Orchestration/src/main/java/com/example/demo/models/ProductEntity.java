package com.example.demo.models;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "products")
public class ProductEntity {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "scrape_response_id", insertable = false, updatable = false)
    private Long scrapeResponseId;
    
    private String name;
    
    @Column(name = "product_url", length = 2048)
    private String url;
    
    private String price;
    
    @Column(name = "image_url", length = 2048)
    private String imageUrl;
    
    @Column(columnDefinition = "TEXT")
    private String description;
    
    @Column(name = "in_stock")
    private Boolean inStock;
    
    @Column(name = "extracted_at")
    private LocalDateTime extractedAt;
    
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public Long getScrapeResponseId() { return scrapeResponseId; }
    public void setScrapeResponseId(Long scrapeResponseId) { this.scrapeResponseId = scrapeResponseId; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
    
    public String getPrice() { return price; }
    public void setPrice(String price) { this.price = price; }
    
    public String getImageUrl() { return imageUrl; }
    public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }
    
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    
    public Boolean getInStock() { return inStock; }
    public void setInStock(Boolean inStock) { this.inStock = inStock; }
    
    public LocalDateTime getExtractedAt() { return extractedAt; }
    public void setExtractedAt(LocalDateTime extractedAt) { this.extractedAt = extractedAt; }
    
    @PrePersist
    protected void onCreate() {
        extractedAt = LocalDateTime.now();
    }
    
    public static ProductEntity fromProduct(Product product) {
        ProductEntity entity = new ProductEntity();
        entity.setName(product.getName());
        entity.setUrl(product.getUrl());
        entity.setPrice(product.getPrice());
        entity.setImageUrl(product.getImageUrl());
        entity.setDescription(product.getDescription());
        entity.setInStock(product.getInStock());
        return entity;
    }
}