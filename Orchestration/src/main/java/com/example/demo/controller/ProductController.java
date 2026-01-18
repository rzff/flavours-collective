package com.example.demo.controller;

import com.example.demo.models.ProductEntity;
import com.example.demo.repository.ProductRepository; // Matches your folder name
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/products")
@CrossOrigin(origins = "http://localhost:3000") // This allows Next.js to talk to Java
public class ProductController {

    private final ProductRepository productRepository;

    public ProductController(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @GetMapping
    public List<ProductEntity> getAllProducts() {
    // This executes: SELECT * FROM products;
    return productRepository.findAll(); 
}
}