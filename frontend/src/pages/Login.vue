<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { setRole, setToken } from "../token";
import { useRouter } from "vue-router";

const router = useRouter();
const loading = ref(false);
const activeTab = ref("login");

const loginForm = reactive({
  role: "student",
  username: "",
  password: "",
  remember: true,
});

const registerForm = reactive({
  role: "student",
  username: "",
  password: "",
  phone: "",
});

function lastRouteKey(username: string) {
  return `da_last_route_${username}`;
}

function goAfterLogin(role: string, username: string) {
  localStorage.setItem("da_last_user", username);
  const last = localStorage.getItem(lastRouteKey(username));
  if (last) {
    if (role === "student" && last.startsWith("/student/")) {
      router.push(last);
      return;
    }
    if ((role === "admin" || role === "teacher") && last.startsWith("/admin/")) {
      router.push(last);
      return;
    }
  }
  if (role === "student") router.push("/student/resource");
  else router.push("/admin/config");
}

async function submitLogin() {
  loading.value = true;
  try {
    const endpoint = loginForm.role === "student" ? "/auth/login/student" : "/auth/login/admin";
    const res = await api.post(endpoint, { username: loginForm.username, password: loginForm.password });
    setToken(res.data.access_token, loginForm.remember ? 7 : 0);
    setRole(res.data.role);
    ElMessage.success("登录成功");
    goAfterLogin(res.data.role, loginForm.username);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "登录失败");
  } finally {
    loading.value = false;
  }
}

async function submitRegister() {
  loading.value = true;
  try {
    const endpoint = registerForm.role === "student" ? "/auth/register/student" : "/auth/register/teacher";
    await api.post(endpoint, {
      username: registerForm.username,
      password: registerForm.password,
      phone: registerForm.phone || undefined,
    });
    ElMessage.success("注册成功，请登录");
    activeTab.value = "login";
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "注册失败");
  } finally {
    loading.value = false;
  }
}

</script>

<template>
  <el-row justify="center" class="login-shell">
    <el-col :span="12" class="login-col">
      <el-card class="login-card">
        <template #header>
          <div class="login-header">
            <div>
              <div class="login-title">账号系统</div>
              <div class="login-subtitle">清新学习风 · 轻松开始</div>
            </div>
          </div>
        </template>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="登录" name="login">
            <el-form label-width="90px" class="login-form">
              <el-form-item label="登录类型">
                <el-radio-group v-model="loginForm.role">
                  <el-radio label="student">学生登录</el-radio>
                  <el-radio label="admin">管理员登录</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" placeholder="请输入账号" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" />
              </el-form-item>
              <el-form-item label="记住登录">
                <el-switch v-model="loginForm.remember" active-text="7天" inactive-text="仅本次" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="loading" @click="submitLogin">登录</el-button>
              </el-form-item>
              <div class="login-tip">
                默认账号：admin/admin123；图谱与题库需在管理端 Seed
              </div>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form label-width="90px" class="login-form">
              <el-form-item label="注册类型">
                <el-radio-group v-model="registerForm.role">
                  <el-radio label="student">学生注册</el-radio>
                  <el-radio label="teacher">教师注册</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="用户名">
                <el-input v-model="registerForm.username" placeholder="设置用户名" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="registerForm.password" type="password" show-password placeholder="设置密码" />
              </el-form-item>
              <el-form-item label="手机号">
                <el-input v-model="registerForm.phone" placeholder="可选，11位手机号" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="loading" @click="submitRegister">注册</el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

        </el-tabs>
      </el-card>
    </el-col>
  </el-row>
</template>

<style scoped>
.login-shell {
  margin-top: 70px;
}

.login-col {
  max-width: 720px;
}

.login-card {
  border-radius: 20px;
  border: 1px solid rgba(46, 88, 63, 0.14);
  box-shadow: 0 20px 50px rgba(27, 55, 40, 0.12);
}

.login-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.login-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.login-subtitle {
  font-size: 12px;
  color: #6b7d72;
  margin-top: 4px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.login-form :deep(.el-input__inner) {
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
}

.login-form :deep(.el-radio) {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
}

.login-form :deep(.el-radio.is-checked) {
  background: rgba(95, 191, 122, 0.12);
  border-color: rgba(95, 191, 122, 0.35);
}

.login-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7d72;
  padding: 8px 12px;
  background: rgba(95, 191, 122, 0.08);
  border-radius: 12px;
}

@media (max-width: 900px) {
  .login-shell {
    margin-top: 40px;
    padding: 0 12px;
  }
  .login-col {
    max-width: 100%;
  }
}
</style>
