package com.example.demo.repository;

import com.example.demo.models.ScrapeResponseEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ScrapeResponseRepository extends JpaRepository<ScrapeResponseEntity, Long> {
    // This gives us all CRUD operations for free:
    // save(), findById(), findAll(), delete(), etc.
}