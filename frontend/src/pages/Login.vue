﻿<script setup lang="ts">
import { computed, reactive, ref } from "vue";
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

const loginAccountLabel = computed(() => (loginForm.role === "student" ? "学号" : "工号/账号"));
const loginAccountPlaceholder = computed(() => (loginForm.role === "student" ? "请输入学号" : "请输入工号或账号"));
const registerAccountLabel = computed(() => (registerForm.role === "student" ? "学号" : "工号"));
const registerAccountPlaceholder = computed(() => (registerForm.role === "student" ? "设置学号" : "设置工号"));

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
    if (role === "admin" && last.startsWith("/admin/")) {
      router.push(last);
      return;
    }
    if (role === "teacher" && last.startsWith("/teacher/")) {
      router.push(last);
      return;
    }
  }
  if (role === "student") router.push("/student/overview");
  else if (role === "teacher") router.push("/teacher/courses");
  else router.push("/admin/dashboard");
}

// 验证登录表单
function validateLoginForm(): boolean {
  if (!validateInput(loginForm.username, 'username')) {
    ElMessage.error('账号长度至少3位，只能包含字母、数字、下划线和连字符');
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
    ElMessage.error('账号长度至少3位，只能包含字母、数字、下划线和连字符');
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
        <div class="brand-kicker">Learning Intelligence</div>
        <div class="brand-logo">CS</div>
        <div class="brand-title">动态评价系统</div>
        <div class="brand-sub">知识图谱 · 自适应练习 · 行为信号</div>
        <div class="brand-desc">
          集成课程、题库与推荐策略，面向计算机专业课程的学习诊断与路径优化。
        </div>
        <div class="brand-points">
          <div class="brand-point">
            <strong>更聚焦</strong>
            <span>把课程、图谱、练习和报告集中到统一学习流程中。</span>
          </div>
          <div class="brand-point">
            <strong>更清晰</strong>
            <span>通过阶段结果和推荐路径帮助学生知道下一步该学什么。</span>
          </div>
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
                  <el-radio label="admin">教师/管理员登录</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item :label="loginAccountLabel">
                <el-input v-model="loginForm.username" :placeholder="loginAccountPlaceholder" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" />
              </el-form-item>
              <el-form-item label="记住登录">
                <el-switch v-model="loginForm.remember" active-text="7天" inactive-text="仅本次" />
              </el-form-item>
              <div class="login-helper-row">
                <span>忘记密码请联系管理员重置</span>
              </div>
              <el-form-item>
                <el-button type="primary" :loading="loading" class="full-btn" @click="submitLogin">登录</el-button>
              </el-form-item>
              <div class="login-tip">
                默认账号：admin/admin123；teacher1/teacher123；student1/student123。
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
              <el-form-item :label="registerAccountLabel">
                <el-input v-model="registerForm.username" :placeholder="registerAccountPlaceholder" />
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
  background: var(--app-bg);
}

.login-shell {
  position: relative;
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  align-items: center;
}

.brand-panel {
  padding: 42px 34px;
  border-radius: calc(var(--app-radius) + 8px);
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.brand-kicker {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #6f87ad;
  font-weight: 800;
  margin-bottom: 18px;
}

.brand-logo {
  width: 66px;
  height: 66px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: #f4f7fb;
  color: var(--app-ink);
  font-weight: 800;
  margin-bottom: 24px;
}

.brand-title {
  font-size: 34px;
  font-weight: 800;
  margin-bottom: 12px;
  color: #22395b;
  line-height: 1.2;
}

.brand-sub {
  color: #5f7698;
  margin-bottom: 18px;
  font-size: 15px;
}

.brand-desc {
  color: #68809d;
  line-height: 1.8;
  font-size: 14px;
  padding: 0;
  margin: 0;
}

.brand-points {
  margin-top: 28px;
  display: grid;
  gap: 12px;
}

.brand-point {
  padding: 14px 16px;
  border-radius: 16px;
  background: #fcfdff;
  border: 1px solid var(--app-border);
  display: grid;
  gap: 4px;
}

.brand-point strong {
  color: #29415f;
}

.brand-point span {
  color: #68809d;
  line-height: 1.7;
  font-size: 13px;
}

.login-card {
  border-radius: calc(var(--app-radius) + 8px);
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
  overflow: hidden;
}

.card-header {
  margin-bottom: 24px;
  padding: 26px 28px 0;
}

.card-title {
  font-size: 24px;
  font-weight: 800;
  color: #22395b;
  margin-bottom: 8px;
}

.card-sub {
  font-size: 14px;
  color: #67809e;
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 24px;
  padding: 0 24px;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--app-border);
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  padding: 12px 20px;
}

.login-form {
  padding: 0 24px 24px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-form-item__label) {
  font-size: 14px;
  font-weight: 500;
  color: var(--app-ink);
}

.login-form :deep(.el-form-item__content) {
  min-height: 44px;
  display: flex;
  align-items: center;
}

.login-form :deep(.el-input) {
  width: 100%;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: var(--app-radius);
  border: none;
  box-shadow: 0 0 0 1px var(--app-border) inset !important;
  min-height: 44px;
  padding: 0 14px;
  background: #fff;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #cdd6e4 inset !important;
}

.login-form :deep(.el-input.is-focus .el-input__wrapper) {
  box-shadow:
    0 0 0 1px var(--app-green) inset,
    0 0 0 3px rgba(79, 140, 255, 0.1) !important;
}

.login-form :deep(.el-input__inner) {
  color: var(--app-ink);
  font-size: 14px;
  height: 42px;
  line-height: 42px;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  padding: 0 !important;
  border-radius: 0 !important;
}

.login-form :deep(.el-radio) {
  margin-right: 12px;
}

.full-btn {
  width: 100%;
  border-radius: var(--app-radius);
  padding: 12px 0;
  font-size: 14px;
  font-weight: 500;
}

.login-helper-row {
  margin: -4px 0 8px;
  display: flex;
  justify-content: flex-end;
  font-size: 12px;
  color: var(--app-ink-soft);
}

.login-tip {
  margin-top: 16px;
  font-size: 13px;
  color: var(--app-ink-soft);
  padding: 12px 16px;
  background: var(--app-bg-alt);
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  line-height: 1.5;
}

@media (max-width: 980px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  
  .brand-panel {
    padding: 32px 24px;
  }
  
  .brand-logo {
    width: 50px;
    height: 50px;
  }
  
  .brand-title {
    font-size: 24px;
  }
  
  .card-header {
    padding: 0 20px;
    padding-top: 20px;
  }
  
  .login-form {
    padding: 0 20px 20px;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 20px 16px;
  }
  
  .brand-panel {
    padding: 24px 20px;
  }
  
  .brand-title {
    font-size: 20px;
  }
  
  .brand-sub {
    font-size: 14px;
  }
  
  .card-title {
    font-size: 18px;
  }
  
  .login-form :deep(.el-form-item) {
    margin-bottom: 16px;
  }
  
  .full-btn {
    padding: 10px 0;
    font-size: 14px;
  }
}
</style>
