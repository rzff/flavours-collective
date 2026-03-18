package com.example.demo.models;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Product {
    private String name;
    private String url;
    
    // The extension sends 'priceRaw', FastAPI sends 'price'
    @JsonAlias({"priceRaw", "price_raw"})
    private String price;
    
    // The extension sends 'imageUrl', FastAPI sends 'image_url'
    @JsonProperty("image_url") 
    @JsonAlias("imageUrl")
    private String imageUrl;
    
    private String description;
    
    // The extension sends 'inStock', FastAPI sends 'in_stock'
    @JsonProperty("in_stock")
    @JsonAlias("inStock")
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