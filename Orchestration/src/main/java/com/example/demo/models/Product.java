package com.example.demo.models;

import com.fasterxml.jackson.annotation.JsonProperty;

public class Product {
    private String name;
    private String url;
    private String price;
    
    @JsonProperty("image_url") // Helps Jackson map Python's snake_case to Java
    private String imageUrl;
    
    private String description;
    
    @JsonProperty("in_stock")
    private Boolean inStock;
    
    // Getters and Setters
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
}