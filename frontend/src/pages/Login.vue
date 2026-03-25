<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { setRole, setToken, validateInput } from "../token";
import { useRouter } from "vue-router";

const router = useRouter();
const loading = ref(false);

const loginForm = reactive({
  role: "student",
  username: "",
  password: "",
  remember: true,
});

const loginAccountLabel = computed(() => (loginForm.role === "student" ? "学号" : "工号/账号"));
const loginAccountPlaceholder = computed(() => (loginForm.role === "student" ? "请输入学号" : "请输入工号或账号"));

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

function validateLoginForm(): boolean {
  if (!validateInput(loginForm.username, "username")) {
    ElMessage.error("账号长度至少3位，只能包含字母、数字、下划线和连字符");
    return false;
  }
  if (!validateInput(loginForm.password, "password")) {
    ElMessage.error("密码长度至少6位");
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
          集成课程、图谱、练习与学习报告，支持管理员统一配置老师和学生账号。
        </div>
        <div class="brand-points">
          <div class="brand-point">
            <strong>账号统一管理</strong>
            <span>老师和学生账号由管理员创建、启用、禁用和重置密码。</span>
          </div>
          <div class="brand-point">
            <strong>不开放注册</strong>
            <span>前台不提供自助注册，避免任意用户自行创建系统账号。</span>
          </div>
        </div>
      </div>

      <el-card class="login-card" shadow="never">
        <div class="card-header">
          <div class="card-title">账号登录</div>
          <div class="card-sub">账号由管理员统一配置，登录后进入对应工作台</div>
        </div>

        <el-form label-width="90px" class="login-form">
          <el-form-item label="登录类型">
            <el-radio-group v-model="loginForm.role">
              <el-radio value="student">学生登录</el-radio>
              <el-radio value="admin">教师/管理员登录</el-radio>
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
            <span>如需新建账号或重置密码，请联系管理员处理</span>
          </div>
          <el-form-item>
            <el-button type="primary" :loading="loading" class="full-btn" @click="submitLogin">登录</el-button>
          </el-form-item>
          <div class="login-tip">
            默认演示账号：admin/admin123；teacher1/teacher123。学生账号由管理员统一配置。
          </div>
        </el-form>
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
  font-size: 40px;
  line-height: 1.05;
  font-weight: 800;
  color: var(--app-ink);
}

.brand-sub {
  margin-top: 10px;
  color: #5d7396;
  font-size: 15px;
}

.brand-desc {
  margin-top: 26px;
  color: #60758f;
  line-height: 1.8;
  font-size: 14px;
}

.brand-points {
  margin-top: 28px;
  display: grid;
  gap: 16px;
}

.brand-point {
  padding: 18px 18px 16px;
  border-radius: 20px;
  background: #f8fbff;
  border: 1px solid #dbe6f2;
}

.brand-point strong {
  display: block;
  margin-bottom: 6px;
  color: #243851;
  font-size: 15px;
}

.brand-point span {
  color: #667c98;
  font-size: 13px;
  line-height: 1.7;
}

.login-card {
  border-radius: calc(var(--app-radius) + 8px);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.card-header {
  margin-bottom: 18px;
}

.card-title {
  font-size: 28px;
  font-weight: 800;
  color: var(--app-ink);
}

.card-sub {
  margin-top: 8px;
  color: #6a7f99;
  font-size: 13px;
}

.login-form {
  margin-top: 10px;
}

.login-helper-row {
  margin: 2px 0 14px;
  color: #6f84a1;
  font-size: 12px;
}

.full-btn {
  width: 100%;
}

.login-tip {
  margin-top: 6px;
  color: #8a9ab0;
  font-size: 12px;
  line-height: 1.7;
}

.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(140, 177, 255, 0.18), transparent 36%),
    radial-gradient(circle at bottom right, rgba(104, 174, 150, 0.18), transparent 32%);
  pointer-events: none;
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .brand-title {
    font-size: 32px;
  }
}
</style>
