package com.example.demo.model;

import lombok.Data;

@Data
public class Product {
    private String name;
    private String url;
    private String price;
    private String imageUrl;
    private String description;
    private Boolean inStock;
}