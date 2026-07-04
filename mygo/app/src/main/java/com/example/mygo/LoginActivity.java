package com.example.mygo; // 替换为你的包名

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.example.mygo.databinding.ActivityLoginBinding;

public class LoginActivity extends AppCompatActivity {

    private ActivityLoginBinding binding;
    private SharedPreferences sharedPreferences;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityLoginBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        // 使用 "user_prefs" 作为文件名来获取 SharedPreferences 实例
        sharedPreferences = getSharedPreferences("user_prefs", MODE_PRIVATE);

        // 检查用户是否已经登录
        if (sharedPreferences.getBoolean("is_logged_in", false)) {
            // 如果已登录，直接跳转到 MainActivity
            startActivity(new Intent(LoginActivity.this, MainActivity.class));
            finish(); // 结束当前 Activity，防止用户按返回键回到登录页
            return;
        }

        // 添加淡入动画
        binding.loginCard.setAlpha(0f);
        binding.loginCard.animate().alpha(1f).setDuration(800).start();

        binding.buttonLogin.setOnClickListener(v -> {
            // 添加按钮点击动画
            v.animate().scaleX(0.95f).scaleY(0.95f).setDuration(100)
                    .withEndAction(() -> {
                        v.animate().scaleX(1f).scaleY(1f).setDuration(100).start();
                        handleLogin();
                    }).start();
        });
        
        binding.buttonGoToRegister.setOnClickListener(v -> {
            // 添加按钮点击动画
            v.animate().scaleX(0.95f).scaleY(0.95f).setDuration(100)
                    .withEndAction(() -> {
                        v.animate().scaleX(1f).scaleY(1f).setDuration(100).start();
                        startActivity(new Intent(LoginActivity.this, RegisterActivity.class));
                    }).start();
        });
    }

    private void handleLogin() {
        String email = binding.editTextEmail.getText().toString().trim();
        String password = binding.editTextPassword.getText().toString().trim();

        if (TextUtils.isEmpty(email) || TextUtils.isEmpty(password)) {
            Toast.makeText(this, "账号和密码不能为空", Toast.LENGTH_SHORT).show();
            return;
        }

        // 从 SharedPreferences 中获取保存的注册信息
        String savedEmail = sharedPreferences.getString("email", "");
        String savedPassword = sharedPreferences.getString("password", "");

        // 验证邮箱和密码
        if (email.equals(savedEmail) && password.equals(savedPassword)) {
            // 登录成功，保存登录状态
            SharedPreferences.Editor editor = sharedPreferences.edit();
            editor.putBoolean("is_logged_in", true);
            editor.apply();

            Toast.makeText(this, "登录成功", Toast.LENGTH_SHORT).show();

            // 跳转到主界面
            Intent intent = new Intent(LoginActivity.this, MainActivity.class);
            startActivity(intent);
            finish(); // 结束当前 Activity
        } else {
            Toast.makeText(this, "账号或密码错误", Toast.LENGTH_SHORT).show();
        }
    }
}