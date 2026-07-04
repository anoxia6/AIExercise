package com.example.mygo;

import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentManager;
import androidx.fragment.app.FragmentTransaction;
import androidx.lifecycle.ViewModelProvider;
import com.example.mygo.databinding.ActivityMainBinding;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.Socket;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainActivity extends AppCompatActivity {

    private ActivityMainBinding binding;
    private ChartViewModel chartViewModel;
    
    // 全局数据接收相关
    private Thread globalDataThread;
    private final Handler uiHandler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean isConnected = new AtomicBoolean(false);
    
    // 开发板连接配置

   private static final String SERVER_IP = "10.41.247.67";
   
    private static final int SERVER_PORT = 9999;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        // 初始化ViewModel
        chartViewModel = new ViewModelProvider(this).get(ChartViewModel.class);

        // 设置底部导航栏的监听器
        binding.bottomNavigation.setOnItemSelectedListener(item -> {
            Fragment selectedFragment = null;
            int itemId = item.getItemId();

            if (itemId == R.id.nav_home) {
                selectedFragment = new HomeFragment();
            } else if (itemId == R.id.nav_videos) {
                selectedFragment = new VideosFragment();
            }

            if (selectedFragment != null) {
                // 调用方法来替换 Fragment
                replaceFragment(selectedFragment);
            }
            return true;
        });

        // 设置默认显示的 Fragment
        if (savedInstanceState == null) {
            binding.bottomNavigation.setSelectedItemId(R.id.nav_home);
        }
        
        // 启动全局数据接收
        startGlobalDataReceiver();
    }

    // 一个用于替换 FrameLayout 中 Fragment 的通用方法
    private void replaceFragment(Fragment fragment) {
        FragmentManager fragmentManager = getSupportFragmentManager();
        FragmentTransaction fragmentTransaction = fragmentManager.beginTransaction();
        fragmentTransaction.replace(R.id.fragment_container, fragment);
        fragmentTransaction.commit();
    }
    
    /**
     * 启动全局数据接收
     */
    private void startGlobalDataReceiver() {
        if (globalDataThread != null && globalDataThread.isAlive()) {
            return; // 线程已在运行
        }
        
        globalDataThread = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                Socket socket = null;
                try {
                    socket = new Socket(SERVER_IP, SERVER_PORT);
                    BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream()));

                    // 连接成功
                    isConnected.set(true);
                    uiHandler.post(() -> {
                        Toast.makeText(this, "已连接到开发板", Toast.LENGTH_SHORT).show();
                    });

                    String line;
                    while (!Thread.currentThread().isInterrupted() && (line = reader.readLine()) != null) {
                        try {
                            JSONObject json = new JSONObject(line);
                            String type = json.optString("type", "data"); // 默认是数据
                            
                            if ("setting".equals(type)) {
                                // 处理设置更新
                                String mode = json.getString("mode");
                                String actMode = json.getString("act_mode");
                                int count = json.getInt("count");
                                int time = json.getInt("time");
                                
                                uiHandler.post(() -> {
                                    if (chartViewModel != null) {
                                        chartViewModel.updateSettings(mode, actMode, count, time);
                                        Toast.makeText(MainActivity.this, "已同步电脑端设置", Toast.LENGTH_SHORT).show();
                                    }
                                });
                                
                            } else {
                                // 处理图表数据更新
                                float count = (float) json.getInt("count");
                                float score = (float) json.getInt("score");
        
                                // 直接在后台线程更新ViewModel数据 (ViewModel已改为线程安全)
                                if (chartViewModel != null) {
                                    chartViewModel.addEntry(new com.github.mikephil.charting.data.Entry(count, score));
                                }
                            }

                        } catch (JSONException e) {
                            // JSON解析错误
                            System.err.println("JSON 解析错误: " + e.getMessage());
                        }
                    }
                } catch (IOException e) {
                    // 网络错误
                    System.err.println("网络连接错误: " + e.getMessage());
                    if (isConnected.get()) {
                        // 之前是连接状态，现在断开了
                        uiHandler.post(() -> {
                            Toast.makeText(this, "连接断开，尝试重连...", Toast.LENGTH_SHORT).show();
                        });
                    }
                } finally {
                    isConnected.set(false);
                    if (socket != null) {
                        try {
                            socket.close();
                        } catch (IOException e) {
                            e.printStackTrace();
                        }
                    }
                }

                // 连接失败或断开后，等待一段时间再重试
                if (!Thread.currentThread().isInterrupted()) {
                    try {
                        Thread.sleep(3000); // 3秒后重试
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt(); // 恢复中断状态
                        break;
                    }
                }
            }
            System.out.println("全局数据接收线程已停止。");
        });
        globalDataThread.start();
    }
    
    /**
     * 发送设置到服务端
     */
    public void sendSettings(String mode, String actMode, int count, int time) {
        new Thread(() -> {
            try {
                if (SERVER_IP == null) {
                    return;
                }
                Socket socket = new Socket(SERVER_IP, SERVER_PORT);
                JSONObject json = new JSONObject();
                json.put("type", "setting");
                json.put("mode", mode);
                json.put("act_mode", actMode);
                json.put("count", count);
                json.put("time", time);
                
                String message = json.toString() + "\n";
                socket.getOutputStream().write(message.getBytes());
                socket.close();
                
                uiHandler.post(() -> {
                    Toast.makeText(this, "设置已同步到电脑", Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                e.printStackTrace();
                uiHandler.post(() -> {
                    Toast.makeText(this, "发送设置失败: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                });
            }
        }).start();
    }

    /**
     * 发送命令到服务端
     */
    public void sendCommand(String cmd) {
        new Thread(() -> {
            try {
                if (SERVER_IP == null) {
                    return;
                }
                Socket socket = new Socket(SERVER_IP, SERVER_PORT);
                JSONObject json = new JSONObject();
                json.put("type", "command");
                json.put("cmd", cmd);
                
                String message = json.toString() + "\n";
                socket.getOutputStream().write(message.getBytes());
                socket.close();
                
                uiHandler.post(() -> {
                    String actionText = "未知";
                    if ("start".equals(cmd)) actionText = "开始运动";
                    else if ("stop".equals(cmd)) actionText = "结束运动";
                    Toast.makeText(this, "已发送指令: " + actionText, Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                e.printStackTrace();
                uiHandler.post(() -> {
                    Toast.makeText(this, "发送指令失败: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                });
            }
        }).start();
    }

    /**
     * 停止全局数据接收
     */
    private void stopGlobalDataReceiver() {
        if (globalDataThread != null) {
            globalDataThread.interrupt();
            globalDataThread = null;
        }
        isConnected.set(false);
    }
    
    /**
     * 获取连接状态
     */
    public boolean isConnected() {
        return isConnected.get();
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        // 停止全局数据接收
        stopGlobalDataReceiver();
    }
}