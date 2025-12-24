package com.example.demo.models;

public class CacheResult {
    private boolean hit;
    private boolean valid;
    private Object cachedData;
    private SelectorInfo selectorInfo;
    
    public boolean isHit() { return hit; }
    public void setHit(boolean hit) { this.hit = hit; }
    
    public boolean isValid() { return valid; }
    public void setValid(boolean valid) { this.valid = valid; }
    
    public Object getCachedData() { return cachedData; }
    public void setCachedData(Object cachedData) { this.cachedData = cachedData; }
    
    public SelectorInfo getSelectorInfo() { return selectorInfo; }
    public void setSelectorInfo(SelectorInfo selectorInfo) { this.selectorInfo = selectorInfo; }
}
