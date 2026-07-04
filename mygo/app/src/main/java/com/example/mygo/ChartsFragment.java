package com.example.mygo;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;

import android.graphics.Color;
import android.widget.TextView;
import com.github.mikephil.charting.charts.LineChart;
import com.github.mikephil.charting.components.XAxis;
import com.github.mikephil.charting.data.Entry;
import com.github.mikephil.charting.data.LineData;
import com.github.mikephil.charting.data.LineDataSet;

import java.util.ArrayList;
import java.util.List;


public class ChartsFragment extends Fragment {
    private LineChart lineChart;
    private ChartViewModel chartViewModel;

    // 添加统计数据的TextView引用
    private TextView tvCurrentScore, tvMaxScore, tvAvgScore;
    
    // 连接状态指示器相关UI元素
    private View statusIndicator;
    private TextView statusText;
    
    // 数据更新定时器
    private android.os.Handler updateHandler;
    private Runnable updateRunnable;


    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_charts, container, false);
        lineChart = view.findViewById(R.id.lineChart);

        // 获取统计数据的TextView引用
        tvCurrentScore = view.findViewById(R.id.tv_current_score);
        tvMaxScore = view.findViewById(R.id.tv_max_score);
        tvAvgScore = view.findViewById(R.id.tv_avg_score);
        
        // 获取连接状态指示器UI元素
        statusIndicator = view.findViewById(R.id.status_indicator);
        statusText = view.findViewById(R.id.status_text);

        // 获取ViewModel（注意用requireActivity()保证同一个ViewModel）
        chartViewModel = new ViewModelProvider(requireActivity()).get(ChartViewModel.class);

        setupChart();
        
        // 恢复统计数据的显示
        restoreStatistics();
        
        // 初始化连接状态
        updateConnectionStatusFromMain();
        
        // 启动数据更新定时器
        startDataUpdateTimer();
        
        return view;
    }

    @Override
    public void onResume() {
        super.onResume();
        // 当 Fragment 可见时，立即更新图表和统计数据
        updateChartDisplay();
        updateConnectionStatusFromMain();
        // 重新启动数据更新定时器
        startDataUpdateTimer();
    }

    @Override
    public void onPause() {
        super.onPause();
        // 停止数据更新定时器
        stopDataUpdateTimer();
    }

    /**
     * 从MainActivity获取连接状态并更新显示
     */
    private void updateConnectionStatusFromMain() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        if (statusIndicator != null && statusText != null) {
            MainActivity mainActivity = (MainActivity) getActivity();
            if (mainActivity != null && mainActivity.isConnected()) {
                // 已连接状态
                statusIndicator.setBackgroundResource(R.drawable.status_connected);
                statusText.setText("已连接");
                statusText.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
            } else {
                // 未连接状态
                statusIndicator.setBackgroundResource(android.R.drawable.presence_invisible);
                statusText.setText("未连接");
                statusText.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
            }
        }
    }
    


    /**
     * 初始化图表的基本样式
     */
    private void setupChart() {
        lineChart.getDescription().setEnabled(true);
        lineChart.getDescription().setText("分数变化实时图表");
        lineChart.setTouchEnabled(true);
        lineChart.setDragEnabled(true);
        lineChart.setScaleEnabled(true);
        lineChart.setPinchZoom(true);
        lineChart.setDrawGridBackground(false);

        // 设置X轴
        XAxis xAxis = lineChart.getXAxis();
        xAxis.setPosition(XAxis.XAxisPosition.BOTTOM);
        xAxis.setDrawGridLines(false);
        xAxis.setGranularity(1f); // 最小间隔为1

        // 初始化一个空的图表数据
        ArrayList<Entry> values = new ArrayList<>();
        // 初始时可以加一个点，也可以不加
        // values.add(new Entry(0, 0));
        LineDataSet set1 = createSet();
        // 用ViewModel里的数据恢复
        List<Entry> entries = chartViewModel.getAllEntries();
        if (!entries.isEmpty()) {
            set1.setValues(entries);
        }
        LineData data = new LineData(set1);
        lineChart.setData(data);
        lineChart.invalidate();
    }

    /**
     * 创建一个新的数据集（一条线）的样式
     */
    private LineDataSet createSet() {
        LineDataSet set = new LineDataSet(null, "分数");
        set.setLineWidth(2.5f);
        set.setColor(Color.rgb(244, 117, 117));
        set.setCircleColor(Color.rgb(244, 117, 117));
        set.setCircleRadius(5f);
        set.setFillColor(Color.rgb(244, 117, 117));
        set.setMode(LineDataSet.Mode.LINEAR);
        //set.setMode(LineDataSet.Mode.CUBIC_BEZIER); // 平滑曲线
        set.setDrawValues(true); // 在点上显示数值
        set.setValueTextSize(10f);
        set.setValueTextColor(Color.BLACK);
        return set;
    }



    /**
     * 更新图表显示（从ViewModel获取最新数据）
     */
    private void updateChartDisplay() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        List<Entry> entries = chartViewModel.getAllEntries();
        
        // 更新图表
        LineDataSet set1 = createSet();
        set1.setValues(entries);
        LineData data = new LineData(set1);
        lineChart.setData(data);
        lineChart.notifyDataSetChanged();
        lineChart.invalidate();
        lineChart.setVisibleXRangeMaximum(10);
        if (!entries.isEmpty()) {
            lineChart.moveViewToX(data.getEntryCount());
        }
        
        // 更新统计数据
        if (!entries.isEmpty()) {
            Entry lastEntry = entries.get(entries.size() - 1);
            updateStatistics(lastEntry.getY());
        } else {
            // 如果没有数据，重置统计显示
            if (tvCurrentScore != null) tvCurrentScore.setText("0");
            if (tvMaxScore != null) tvMaxScore.setText("0");
            if (tvAvgScore != null) tvAvgScore.setText("0");
        }
    }

    /**
     * 恢复统计数据的显示（当Fragment重新创建时调用）
     */
    private void restoreStatistics() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        // 从ViewModel获取最新的统计数据
        float currentScore = chartViewModel.getCurrentScore();
        float maxScore = chartViewModel.getMaxScore();
        float avgScore = chartViewModel.getAverageScore();
        
        // 更新UI显示
        if (tvCurrentScore != null) {
            tvCurrentScore.setText(String.valueOf((int) currentScore));
        }
        if (tvMaxScore != null) {
            tvMaxScore.setText(String.valueOf((int) maxScore));
        }
        if (tvAvgScore != null) {
            tvAvgScore.setText(String.valueOf((int) avgScore));
        }
    }

    /**
     * 更新统计数据
     * @param currentScore 当前分数
     */
    private void updateStatistics(float currentScore) {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        List<Entry> entries = chartViewModel.getAllEntries();

        // 更新当前分数
        if (tvCurrentScore != null) {
            tvCurrentScore.setText(String.valueOf((int) currentScore));
        }

        // 计算最高分
        float maxScore = 0;
        for (Entry entry : entries) {
            if (entry.getY() > maxScore) {
                maxScore = entry.getY();
            }
        }
        if (tvMaxScore != null) {
            tvMaxScore.setText(String.valueOf((int) maxScore));
        }

        // 计算平均分
        float totalScore = 0;
        for (Entry entry : entries) {
            totalScore += entry.getY();
        }
        float avgScore = entries.isEmpty() ? 0 : totalScore / entries.size();
        if (tvAvgScore != null) {
            tvAvgScore.setText(String.valueOf((int) avgScore));
        }
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        // 停止数据更新定时器
        stopDataUpdateTimer();
    }
    
    /**
     * 启动数据更新定时器
     */
    private void startDataUpdateTimer() {
        if (updateHandler == null) {
            updateHandler = new android.os.Handler(android.os.Looper.getMainLooper());
        }
        
        if (updateRunnable == null) {
            updateRunnable = new Runnable() {
                @Override
                public void run() {
                    updateChartDisplay();
                    updateConnectionStatusFromMain();
                    // 每500毫秒更新一次，确保实时性
                    updateHandler.postDelayed(this, 500);
                }
            };
        }
        
        updateHandler.post(updateRunnable);
    }
    
    /**
     * 停止数据更新定时器
     */
    private void stopDataUpdateTimer() {
        if (updateHandler != null && updateRunnable != null) {
            updateHandler.removeCallbacks(updateRunnable);
        }
    }
}