package com.example.demo.repository;

import com.example.demo.models.ProductEntity; // Point to the Entity
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {
}