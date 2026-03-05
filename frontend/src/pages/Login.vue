<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { setRole, setToken, validateInput } from "../token";
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

// 验证登录表单
function validateLoginForm(): boolean {
  if (!validateInput(loginForm.username, 'username')) {
    ElMessage.error('用户名长度至少3位，只能包含字母、数字、下划线和连字符');
    return false;
  }
  if (!validateInput(loginForm.password, 'password')) {
    ElMessage.error('密码长度至少6位');
    return false;
  }
  return true;
}

// 验证注册表单
function validateRegisterForm(): boolean {
  if (!validateInput(registerForm.username, 'username')) {
    ElMessage.error('用户名长度至少3位，只能包含字母、数字、下划线和连字符');
    return false;
  }
  if (!validateInput(registerForm.password, 'password')) {
    ElMessage.error('密码长度至少6位');
    return false;
  }
  if (registerForm.phone && !/^1[3-9]\d{9}$/.test(registerForm.phone)) {
    ElMessage.error('请输入有效的11位手机号');
    return false;
  }
  return true;
}

async function submitLogin() {
  if (!validateLoginForm()) return;
  
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
  if (!validateRegisterForm()) return;
  
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
  <div class="login-page">
    <div class="login-bg" />
    <div class="login-shell">
      <div class="brand-panel">
        <div class="brand-logo">CS</div>
        <div class="brand-title">动态评价系统</div>
        <div class="brand-sub">知识图谱 · 自适应练习 · 行为信号</div>
        <div class="brand-desc">
          集成课程、题库与推荐策略，面向计算机专业课程的学习诊断与路径优化。
        </div>
      </div>

      <el-card class="login-card" shadow="never">
        <div class="card-header">
          <div class="card-title">账号系统</div>
          <div class="card-sub">登录后进入学习/管理工作台</div>
        </div>

        <el-tabs v-model="activeTab" class="login-tabs">
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
                <el-button type="primary" :loading="loading" class="full-btn" @click="submitLogin">登录</el-button>
              </el-form-item>
              <div class="login-tip">
                默认账号：admin/admin123；图谱与题库需在管理端 Seed。
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
                <el-button type="primary" :loading="loading" class="full-btn" @click="submitRegister">注册</el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
}

.login-bg {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(900px 500px at 15% 20%, rgba(79, 140, 255, 0.08), transparent 60%),
    radial-gradient(800px 480px at 85% 25%, rgba(86, 191, 255, 0.06), transparent 60%),
    linear-gradient(160deg, var(--app-bg) 0%, var(--app-bg-alt) 45%, #f0f2f5 100%);
  z-index: 0;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
}

.brand-panel {
  padding: 28px 24px;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  box-shadow: var(--app-shadow);
}

.brand-logo {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, var(--app-green), #7fb0ff);
  color: #fff;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(79, 140, 255, 0.2);
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--app-ink);
}

.brand-sub {
  color: var(--app-ink-soft);
  margin-bottom: 16px;
}

.brand-desc {
  color: var(--app-ink-soft);
  line-height: 1.7;
  font-size: 14px;
}

.login-card {
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: var(--app-shadow);
}

.card-header {
  margin-bottom: 12px;
}

.card-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--app-ink);
}

.card-sub {
  font-size: 12px;
  color: var(--app-ink-soft);
  margin-top: 6px;
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--app-border);
}

.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.login-form :deep(.el-input__inner) {
  border-radius: var(--app-radius);
  background: transparent;
  border-color: transparent;
  color: var(--app-ink);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: var(--el-text-color-placeholder);
}

.login-form :deep(.el-input__wrapper) {
  background: #f8f9fa;
  box-shadow: inset 0 0 0 1px var(--app-border);
}

.login-form :deep(.el-radio) {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid transparent;
}

.login-form :deep(.el-radio.is-checked) {
  background: rgba(79, 140, 255, 0.08);
  border-color: rgba(79, 140, 255, 0.3);
}

.full-btn {
  width: 100%;
  border-radius: var(--app-radius);
  padding: 10px 0;
}

.login-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--app-ink-soft);
  padding: 8px 12px;
  background: rgba(79, 140, 255, 0.05);
  border-radius: var(--app-radius);
  border: 1px solid rgba(79, 140, 255, 0.1);
}

@media (max-width: 980px) {
  .login-shell {
    grid-template-columns: 1fr;
  }
}
</style>
