package com.example.demo.models;

public class CacheInfo {
    private String key;
    private long timestamp;
    private SelectorInfo selectorInfo;
    
    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }
    
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    
    public SelectorInfo getSelectorInfo() { return selectorInfo; }
    public void setSelectorInfo(SelectorInfo selectorInfo) { this.selectorInfo = selectorInfo; }
}
