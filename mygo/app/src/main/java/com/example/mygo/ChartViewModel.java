package com.example.mygo;

import androidx.lifecycle.MutableLiveData;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.ViewModel;
import com.github.mikephil.charting.data.Entry;
import java.util.ArrayList;
import java.util.List;

public class ChartViewModel extends ViewModel {
    private final List<Entry> allEntries = new ArrayList<>();
    
    // 用于通知 Fragment 数据更新
    private final MutableLiveData<List<Entry>> entriesLiveData = new MutableLiveData<>();
    
    // 用于通知 Fragment 设置更新 (来自PC)
    private final MutableLiveData<SettingModel> settingsLiveData = new MutableLiveData<>();

    public LiveData<List<Entry>> getEntriesLiveData() {
        return entriesLiveData;
    }
    
    public LiveData<SettingModel> getSettingsLiveData() {
        return settingsLiveData;
    }
    
    // 添加统计数据字段，用于保存最新的统计数据
    private volatile float currentScore = 0;
    private volatile float maxScore = 0;
    private volatile float averageScore = 0;
    private volatile float totalScoreSum = 0; // Running sum for O(1) average calculation

    public synchronized List<Entry> getAllEntries() {
        return allEntries;
    }
    

    
    public void updateSettings(String mode, String actMode, int count, int time) {
        settingsLiveData.postValue(new SettingModel(mode, actMode, count, time));
    }
    
    public static class SettingModel {
        public String mode;
        public String actMode;
        public int count;
        public int time;
        
        public SettingModel(String mode, String actMode, int count, int time) {
            this.mode = mode;
            this.actMode = actMode;
            this.count = count;
            this.time = time;
        }
    }

    public synchronized void addEntry(Entry entry) {
        allEntries.add(entry);
        // 每次添加新数据时，更新统计数据
        updateStatistics(entry.getY());
    }

    public synchronized void clear() {
        allEntries.clear();
        // 清空时重置统计数据
        currentScore = 0;
        maxScore = 0;
        averageScore = 0;
        totalScoreSum = 0;
    }
    
    /**
     * 更新统计数据 (Optimized to O(1))
     */
    private void updateStatistics(float newScore) {
        currentScore = newScore;
        
        // 更新最高分
        if (newScore > maxScore) {
            maxScore = newScore;
        }
        
        // 更新平均分
        totalScoreSum += newScore;
        if (!allEntries.isEmpty()) {
            averageScore = totalScoreSum / allEntries.size();
        }
    }
    
    /**
     * 获取最高分
     */
    public float getMaxScore() {
        return maxScore;
    }
    
    /**
     * 获取平均分
     */
    public float getAverageScore() {
        return averageScore;
    }
    
    /**
     * 获取当前分数（最新分数）
     */
    public float getCurrentScore() {
        return currentScore;
    }
}