package com.example.mygo;

import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.example.mygo.databinding.ActivityRegisterBinding;

public class RegisterActivity extends AppCompatActivity {

    private ActivityRegisterBinding binding;
    private SharedPreferences sharedPreferences;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityRegisterBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        sharedPreferences = getSharedPreferences("user_prefs", MODE_PRIVATE);

        // 添加淡入动画
        binding.registerCard.setAlpha(0f);
        binding.registerCard.animate().alpha(1f).setDuration(800).start();

        binding.buttonRegister.setOnClickListener(v -> {
            // 添加按钮点击动画
            v.animate().scaleX(0.95f).scaleY(0.95f).setDuration(100)
                    .withEndAction(() -> {
                        v.animate().scaleX(1f).scaleY(1f).setDuration(100).start();
                        handleRegister();
                    }).start();
        });
    }

    private void handleRegister() {
        String email = binding.editTextEmail.getText().toString().trim();
        String password = binding.editTextPassword.getText().toString().trim();

        if (TextUtils.isEmpty(email) || TextUtils.isEmpty(password)) {
            Toast.makeText(this, "邮箱和密码不能为空", Toast.LENGTH_SHORT).show();
            return;
        }

        // 使用 SharedPreferences.Editor 来保存数据
        SharedPreferences.Editor editor = sharedPreferences.edit();
        editor.putString("email", email);
        editor.putString("password", password);
        editor.apply(); // 使用 apply() 在后台异步保存

        Toast.makeText(this, "注册成功！", Toast.LENGTH_SHORT).show();

        // 注册成功后，结束当前页面，返回登录页
        finish();
    }
}