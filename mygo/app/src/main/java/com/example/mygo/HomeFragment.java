package com.example.mygo;

import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;
import com.example.mygo.databinding.FragmentHomeBinding;
import com.github.mikephil.charting.charts.LineChart;
import com.github.mikephil.charting.components.XAxis;
import com.github.mikephil.charting.data.Entry;
import com.github.mikephil.charting.data.LineData;
import com.github.mikephil.charting.data.LineDataSet;
import android.graphics.Color;
import java.util.ArrayList;
import java.util.List;

public class HomeFragment extends Fragment {

    private FragmentHomeBinding binding;
    private SharedPreferences sharedPreferences;
    
    // 快捷操作按钮引用
    private View btnSetGoal;
    private android.widget.Button btnStartExercise, btnEndExercise;
    
    // 目标完成度相关UI元素
    private TextView tvProgressPercent, tvGoalCount, tvCurrentCount, tvProgressMessage;
    private ProgressBar progressGoal;
    
    // 图表引用
    private LineChart lineChart;
    
    // 运动卡片相关UI元素
    private TextView tvWorkoutCount, tvWorkoutDuration;
    
    // ViewModel用于获取图表数据
    private ChartViewModel chartViewModel;
    
    // 数据更新定时器
    private android.os.Handler updateHandler;
    private Runnable updateRunnable;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        binding = FragmentHomeBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        sharedPreferences = getActivity().getSharedPreferences("user_prefs", Context.MODE_PRIVATE);

        // 初始化UI元素
        initUIElements();
        
        // 设置用户信息
        setupUserInfo();
        
        // 设置点击事件
        setupClickListeners();
        
        // 初始化目标完成度显示
        updateGoalProgress();
        
        // 启动数据更新定时器
        startDataUpdateTimer();
        
        // 观察设置变化
        chartViewModel.getSettingsLiveData().observe(getViewLifecycleOwner(), setting -> {
            if (setting != null) {
                // 更新UI显示的逻辑可以更复杂，例如直接弹出Dialog或者Toast
                // 这里我们至少要更新本地的首选项，以便 Goal Progress 正确显示
                int goal = (setting.mode.equals("count")) ? setting.count : setting.time;
                if (goal > 0) {
                     sharedPreferences.edit().putInt("daily_goal", goal).apply();
                     updateGoalProgress();
                }
                // 可能还需要显示当前的模式和动作
                String modeText = (setting.mode.equals("count")) ? "计数模式" : "计时模式";
                String actText = "未知模式";
                if ("squat".equals(setting.actMode)) actText = "深蹲";
                else if ("pushup".equals(setting.actMode)) actText = "俯卧撑";
                else if ("situp".equals(setting.actMode)) actText = "仰卧起坐";
                
                binding.tvWechatId.setText("当前模式: " + actText + " (" + modeText + ")");
            }
        });
    }

    /**
     * 初始化UI元素
     */
    private void initUIElements() {
        btnSetGoal = getView().findViewById(R.id.btn_set_goal);
        btnStartExercise = getView().findViewById(R.id.btn_start_exercise);
        btnEndExercise = getView().findViewById(R.id.btn_end_exercise);
        
        // 目标完成度相关UI元素
        tvProgressPercent = getView().findViewById(R.id.tv_progress_percent);
        tvGoalCount = getView().findViewById(R.id.tv_goal_count);
        tvCurrentCount = getView().findViewById(R.id.tv_current_count);
        tvProgressMessage = getView().findViewById(R.id.tv_progress_message);
        progressGoal = getView().findViewById(R.id.progress_goal);
        
        // 运动卡片相关UI元素
        tvWorkoutCount = getView().findViewById(R.id.tv_workout_count);
        tvWorkoutDuration = getView().findViewById(R.id.tv_workout_duration);
        
        // 获取ViewModel
        chartViewModel = new ViewModelProvider(requireActivity()).get(ChartViewModel.class);
        
        // 初始化图表
        lineChart = getView().findViewById(R.id.lineChart);
        setupChart();
    }

    /**
     * 设置用户信息
     */
    private void setupUserInfo() {
        // 读取昵称
        String nickname = sharedPreferences.getString("nickname", "运动达人");
        binding.etNickname.setText(nickname);

        // 读取个性签名
        String signature = sharedPreferences.getString("signature", "今天也要加油运动哦！💪");
        binding.etSignature.setText(signature);

        // 读取账号（email）
        String account = sharedPreferences.getString("email", "user@mygo.com");
        binding.tvWechatId.setText("SportAI账号：" + account);

        // 监听昵称变化并保存
        binding.etNickname.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override
            public void afterTextChanged(Editable s) {
                sharedPreferences.edit().putString("nickname", s.toString()).apply();
            }
        });

        // 监听个性签名变化并保存
        binding.etSignature.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override
            public void afterTextChanged(Editable s) {
                sharedPreferences.edit().putString("signature", s.toString()).apply();
            }
        });
    }

    /**
     * 设置点击事件
     */
    private void setupClickListeners() {
        // 设置目标按钮
        btnSetGoal.setOnClickListener(v -> {
            // 检查Fragment是否仍然附加到上下文
            if (!isAdded() || getContext() == null) {
                return;
            }
            showGoalSettingDialog();
        });

        // 开始运动按钮
        btnStartExercise.setOnClickListener(v -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).sendCommand("start");
            }
        });

        // 结束运动按钮
        btnEndExercise.setOnClickListener(v -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).sendCommand("stop");
            }
        });

        // 登出按钮
        binding.buttonLogout.setOnClickListener(v -> {
            // 检查Fragment是否仍然附加到上下文
            if (!isAdded() || getContext() == null) {
                return;
            }
            
            // 获取 SharedPreferences
            SharedPreferences.Editor editor = sharedPreferences.edit();

            // 清除登录状态
            editor.putBoolean("is_logged_in", false);
            editor.apply();

            // 跳转回登录页面
            Intent intent = new Intent(getActivity(), LoginActivity.class);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
        });
    }

    /**
     * 显示目标设置对话框
     */
    private void showGoalSettingDialog() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        AlertDialog.Builder builder = new AlertDialog.Builder(getContext());
        builder.setTitle("设置运动目标");

        // 创建自定义布局
        android.widget.LinearLayout layout = new android.widget.LinearLayout(getContext());
        layout.setOrientation(android.widget.LinearLayout.VERTICAL);
        layout.setPadding(50, 40, 50, 40);

        // 1. 模式选择 (计数/计时)
        TextView tvMode = new TextView(getContext());
        tvMode.setText("选择模式:");
        layout.addView(tvMode);

        android.widget.RadioGroup rgMode = new android.widget.RadioGroup(getContext());
        rgMode.setOrientation(android.widget.LinearLayout.HORIZONTAL);
        
        android.widget.RadioButton rbCount = new android.widget.RadioButton(getContext());
        rbCount.setText("计数模式");
        rbCount.setId(View.generateViewId());
        rbCount.setChecked(true); // 默认选中
        
        android.widget.RadioButton rbTime = new android.widget.RadioButton(getContext());
        rbTime.setText("计时模式");
        rbTime.setId(View.generateViewId());
        
        rgMode.addView(rbCount);
        rgMode.addView(rbTime);
        layout.addView(rgMode);

        // 2. 动作选择
        TextView tvAction = new TextView(getContext());
        tvAction.setText("选择动作:");
        tvAction.setPadding(0, 20, 0, 0);
        layout.addView(tvAction);

        android.widget.Spinner spinnerAction = new android.widget.Spinner(getContext());
        String[] actions = {"深蹲模式", "俯卧撑模式", "仰卧起坐模式"};
        android.widget.ArrayAdapter<String> adapter = new android.widget.ArrayAdapter<>(
                getContext(), android.R.layout.simple_spinner_dropdown_item, actions);
        spinnerAction.setAdapter(adapter);
        layout.addView(spinnerAction);

        // 3. 目标数值 (次数/时间)
        TextView tvTarget = new TextView(getContext());
        tvTarget.setText("目标次数:");
        tvTarget.setPadding(0, 20, 0, 0);
        layout.addView(tvTarget);

        final EditText input = new EditText(getContext());
        input.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        input.setText("10"); // 默认值
        layout.addView(input);

        // 监听模式切换，更新输入提示
        rgMode.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == rbCount.getId()) {
                tvTarget.setText("目标次数:");
                input.setHint("请输入目标次数");
                input.setText("10");
            } else {
                tvTarget.setText("目标时间(秒):");
                input.setHint("请输入目标时间(秒)");
                input.setText("60");
            }
        });

        builder.setView(layout);

        builder.setPositiveButton("同步并设置", (dialog, which) -> {
            String valStr = input.getText().toString();
            if (!valStr.isEmpty()) {
                try {
                    int val = Integer.parseInt(valStr);
                    if (val > 0) {
                        // 收集数据
                        String mode = (rgMode.getCheckedRadioButtonId() == rbCount.getId()) ? "count" : "time";
                        String selectedAction = (String) spinnerAction.getSelectedItem();
                        String actMode = "squat";
                        if (selectedAction.equals("俯卧撑模式")) actMode = "pushup";
                        else if (selectedAction.equals("仰卧起坐模式")) actMode = "situp";
                        
                        int count = (mode.equals("count")) ? val : 0;
                        int time = (mode.equals("time")) ? val : 0;

                        // 保存本地目标 (无论是次数还是时间，都暂时存为 goal 以供进度条显示，虽然时间模式下进度条可能意义不同)
                        // 如果是时间模式，进度条可能需要改为显示时间进度，但这里先主要同步给PC
                        if (mode.equals("count")) {
                            sharedPreferences.edit().putInt("daily_goal", count).apply();
                        } else {
                             // 时间模式下，本地目标暂存为时间值，虽然Home页逻辑是按次数算的
                             // 这是一个小的UI不一致点，但主要功能是同步。
                             sharedPreferences.edit().putInt("daily_goal", val).apply(); 
                        }
                        
                        updateGoalProgress();

                        // 发送给PC
                        if (getActivity() instanceof MainActivity) {
                            ((MainActivity) getActivity()).sendSettings(mode, actMode, count, time);
                        }

                    } else {
                        Toast.makeText(getContext(), "请输入大于0的数字", Toast.LENGTH_SHORT).show();
                    }
                } catch (NumberFormatException e) {
                    Toast.makeText(getContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show();
                }
            } else {
                Toast.makeText(getContext(), "请输入数值", Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNegativeButton("取消", (dialog, which) -> dialog.cancel());

        builder.show();
    }

    /**
     * 更新目标完成度显示
     */
    private void updateGoalProgress() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        // 获取今日目标
        int dailyGoal = sharedPreferences.getInt("daily_goal", 0);
        
        // 获取当前完成次数（从ChartViewModel获取）
        int currentCount = chartViewModel.getAllEntries().size();
        
        // 更新运动卡片数据
        updateWorkoutData(currentCount);
        
        // 更新UI显示
        if (dailyGoal > 0) {
            if (tvGoalCount != null) tvGoalCount.setText(String.valueOf(dailyGoal));
            if (tvCurrentCount != null) tvCurrentCount.setText(String.valueOf(currentCount));
            
            // 计算完成度百分比
            int progressPercent = (int)((currentCount * 100.0) / dailyGoal);
            if (progressPercent > 100) progressPercent = 100;
            
            // 更新进度条
            if (progressGoal != null) progressGoal.setProgress(progressPercent);
            if (tvProgressPercent != null) tvProgressPercent.setText(progressPercent + "%");
            
            // 根据完成情况设置颜色和消息
            if (progressPercent >= 100) {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                if (progressPercent > 100) {
                    if (tvProgressMessage != null) {
                        tvProgressMessage.setText("🎉 超额完成！继续保持！");
                        tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                    }
                } else {
                    if (tvProgressMessage != null) {
                        tvProgressMessage.setText("🎉 目标完成！太棒了！");
                        tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                    }
                }
            } else if (progressPercent >= 80) {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_orange_dark));
                if (tvProgressMessage != null) {
                    tvProgressMessage.setText("💪 接近目标，继续加油！");
                    tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_orange_dark));
                }
            } else if (progressPercent >= 50) {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_blue_dark));
                if (tvProgressMessage != null) {
                    tvProgressMessage.setText("👍 完成过半，继续努力！");
                    tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_blue_dark));
                }
            } else {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
                if (tvProgressMessage != null) {
                    tvProgressMessage.setText("⏰ 还需努力，加油！");
                    tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
                }
            }
        } else {
            // 未设置目标
            if (tvGoalCount != null) tvGoalCount.setText("未设置");
            if (tvCurrentCount != null) tvCurrentCount.setText(String.valueOf(currentCount));
            if (progressGoal != null) progressGoal.setProgress(0);
            if (tvProgressPercent != null) tvProgressPercent.setText("0%");
            if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.darker_gray));
            if (tvProgressMessage != null) {
                tvProgressMessage.setText("请先设置今日目标");
                tvProgressMessage.setTextColor(getResources().getColor(android.R.color.darker_gray));
            }
        }
    }

    /**
     * 更新运动数据
     */
    private void updateWorkoutData(int workoutCount) {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        // 更新运动次数
        if (tvWorkoutCount != null) {
            tvWorkoutCount.setText(String.valueOf(workoutCount));
        }
        
        // 计算运动时长（每次运动增加约4秒）
        double workoutDuration = workoutCount * (1.0 / 15.0);
        if (tvWorkoutDuration != null) {
            // 保留一位小数显示
            String durationText = String.format("%.1f", workoutDuration);
            tvWorkoutDuration.setText(durationText);
        }
    }

    /**
     * 初始化图表的基本样式
     */
    private void setupChart() {
        if (lineChart == null) return;
        lineChart.getDescription().setEnabled(false);
        lineChart.setTouchEnabled(true);
        lineChart.setDragEnabled(true);
        lineChart.setScaleEnabled(true);
        lineChart.setPinchZoom(true);
        lineChart.setDrawGridBackground(false);

        XAxis xAxis = lineChart.getXAxis();
        xAxis.setPosition(XAxis.XAxisPosition.BOTTOM);
        xAxis.setDrawGridLines(false);
        xAxis.setGranularity(1f);

        LineDataSet set1 = createSet();
        List<Entry> entries = chartViewModel.getAllEntries();
        if (!entries.isEmpty()) {
            set1.setValues(entries);
        }
        LineData data = new LineData(set1);
        lineChart.setData(data);
        lineChart.invalidate();
    }

    private LineDataSet createSet() {
        LineDataSet set = new LineDataSet(null, "分数");
        set.setLineWidth(2.5f);
        set.setColor(Color.parseColor("#FF5E00"));
        set.setCircleColor(Color.parseColor("#FF5E00"));
        set.setCircleRadius(4f);
        set.setFillColor(Color.parseColor("#FF5E00"));
        set.setMode(LineDataSet.Mode.LINEAR);
        set.setDrawValues(true);
        set.setValueTextSize(10f);
        set.setValueTextColor(Color.BLACK);
        return set;
    }

    private void updateChartDisplay() {
        if (!isAdded() || getContext() == null || lineChart == null) return;
        List<Entry> entries = chartViewModel.getAllEntries();
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
    }

    @Override
    public void onResume() {
        super.onResume();
        // 每次回到主页时更新目标完成度
        updateGoalProgress();
        // 重新启动数据更新定时器
        startDataUpdateTimer();
    }
    
    @Override
    public void onPause() {
        super.onPause();
        // 停止数据更新定时器
        stopDataUpdateTimer();
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        // 停止数据更新定时器
        stopDataUpdateTimer();
        binding = null; // 避免内存泄漏
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
                    updateGoalProgress();
                    updateChartDisplay();
                    // 每秒更新一次
                    updateHandler.postDelayed(this, 1000);
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