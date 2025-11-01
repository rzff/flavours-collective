package com.example.demo.model;

import lombok.Data;
import java.util.Map;
import java.util.List;

@Data
public class SelectorInfo {
    private String mainSelector;
    private Map<String, List<String>> fieldSelectors;
    private String pageType;
    private String platform;
}