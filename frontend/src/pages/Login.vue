<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { setRole, setToken, validateInput } from "../token";
import { useRoute, useRouter } from "vue-router";
import { User, Lock, ArrowRight } from "@element-plus/icons-vue";

const router = useRouter();
const route = useRoute();
const loading = ref(false);

const mode = computed<"student" | "staff">(() =>
  route.path === "/login/staff" ? "staff" : "student",
);

const loginForm = reactive({
  username: "",
  password: "",
  remember: true,
});

const loginAccountLabel = computed(() => (mode.value === "student" ? "学号" : "工号 / 账号"));
const loginAccountPlaceholder = computed(() =>
  mode.value === "student" ? "请输入学号" : "请输入工号或管理员账号",
);

const cardTitle = computed(() =>
  mode.value === "student" ? "学生登录" : "教师 / 管理员登录",
);
const cardSubtitle = computed(() =>
  mode.value === "student"
    ? "请使用学号与密码进入学习端"
    : "请使用教师或管理员账号进入系统",
);

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
  if (role === "student") router.push("/student/dashboard");
  else if (role === "teacher") router.push("/teacher/workspace");
  else router.push("/admin/dashboard");
}

function validateLoginForm(): boolean {
  if (!validateInput(loginForm.username, "username")) {
    ElMessage.error("账号长度至少 3 位，且只能包含字母、数字、下划线或连字符");
    return false;
  }
  if (!validateInput(loginForm.password, "password")) {
    ElMessage.error("密码长度至少 6 位");
    return false;
  }
  return true;
}

async function submitLogin() {
  if (!validateLoginForm()) return;
  loading.value = true;
  try {
    const endpoint = mode.value === "student" ? "/auth/login/student" : "/auth/login/admin";
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
  <div class="login-container">
    <div class="mesh-gradient"></div>

    <main class="login-content">
      <div class="login-shell">
        <section class="brand-section">
          <div class="brand-badge">Dynamic Assessment 2.0</div>
          <h1 class="brand-title">
            释放数据价值
            <span class="text-gradient">重塑评价体系</span>
          </h1>
          <p class="brand-description">
            基于知识图谱与动态行为分析，为每一位学习者构建精准的能力画像。
          </p>

          <div class="feature-list">
            <div class="feature-item">
              <div class="feature-icon">◎</div>
              <div class="feature-text">
                <h3>自适应练习</h3>
                <p>根据掌握度动态调整学习节奏</p>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">◈</div>
              <div class="feature-text">
                <h3>多维能力画像</h3>
                <p>持续反馈学习状态与阶段变化</p>
              </div>
            </div>
          </div>
        </section>

        <section class="form-section">
          <div class="login-card glass-card">
            <header class="card-header">
              <h2>{{ cardTitle }}</h2>
              <p>{{ cardSubtitle }}</p>
            </header>

            <div class="role-selector" role="tablist" aria-label="选择登录入口">
              <router-link
                to="/login/student"
                class="role-tab"
                :class="{ active: mode === 'student' }"
                role="tab"
                :aria-selected="mode === 'student'"
              >
                学生登录
              </router-link>
              <router-link
                to="/login/staff"
                class="role-tab"
                :class="{ active: mode === 'staff' }"
                role="tab"
                :aria-selected="mode === 'staff'"
              >
                教师 / 管理员
              </router-link>
            </div>

            <form class="login-form" @submit.prevent="submitLogin">
              <div class="form-group">
                <label>{{ loginAccountLabel }}</label>
                <el-input
                  v-model="loginForm.username"
                  :placeholder="loginAccountPlaceholder"
                  :prefix-icon="User"
                />
              </div>

              <div class="form-group">
                <label>密码</label>
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  show-password
                  placeholder="请输入密码"
                  :prefix-icon="Lock"
                />
              </div>

              <div class="form-footer">
                <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
                <a href="#" class="forgot-pwd">忘记密码？</a>
              </div>

              <el-button
                type="primary"
                class="login-btn"
                :loading="loading"
                @click="submitLogin"
              >
                立即登录
                <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
            </form>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background-color: var(--app-bg);
}

.mesh-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(at 0% 0%, color-mix(in srgb, var(--app-primary) 14%, transparent) 0px, transparent 50%),
    radial-gradient(at 100% 0%, color-mix(in srgb, var(--app-info) 14%, transparent) 0px, transparent 50%),
    radial-gradient(at 100% 100%, color-mix(in srgb, var(--app-success) 8%, transparent) 0px, transparent 50%),
    radial-gradient(at 0% 100%, color-mix(in srgb, var(--app-warning) 8%, transparent) 0px, transparent 50%);
  filter: blur(84px);
  z-index: 0;
}

.login-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1120px;
  padding: 32px 24px;
}

.login-shell {
  display: grid;
  grid-template-columns: 1fr 460px;
  gap: 56px;
  align-items: center;
}

.brand-section {
  animation: slideInLeft 0.6s ease-out;
}

@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-24px); }
  to { opacity: 1; transform: translateX(0); }
}

.brand-badge {
  display: inline-block;
  padding: 6px 14px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  border-radius: 999px;
  font-size: var(--app-text-sm);
  font-weight: 700;
  margin-bottom: 18px;
}

.brand-title {
  font-size: clamp(38px, 4.4vw, 56px);
  line-height: 1.12;
  font-weight: 900;
  color: var(--app-text-main);
  margin-bottom: 18px;
  letter-spacing: -0.04em;
}

.text-gradient {
  background: var(--app-gradient-primary);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-description {
  font-size: var(--app-text-md);
  color: var(--app-text-soft);
  max-width: 420px;
  line-height: 1.8;
}

.feature-list {
  display: grid;
  gap: 20px;
  margin-top: 26px;
}

.feature-item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.feature-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--app-card);
  color: var(--app-primary);
  font-size: 18px;
  font-weight: 700;
  box-shadow: var(--app-shadow-soft);
}

.feature-text h3 {
  margin: 0 0 4px;
  font-size: var(--app-text-base);
  font-weight: 700;
  color: var(--app-text-main);
}

.feature-text p {
  margin: 0;
  font-size: var(--app-text-sm);
  line-height: 1.7;
  color: var(--app-text-soft);
}

.form-section {
  display: flex;
  justify-content: flex-end;
  animation: slideInRight 0.6s ease-out;
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(24px); }
  to { opacity: 1; transform: translateX(0); }
}

.login-card {
  width: 100%;
  max-width: 440px;
  padding: 30px 28px 26px;
  border-radius: 30px;
}

.card-header {
  margin-bottom: 22px;
  text-align: center;
}

.card-header h2 {
  font-size: 24px;
  font-weight: 800;
  color: var(--app-text-main);
  margin-bottom: 8px;
}

.card-header p {
  color: var(--app-text-soft);
  font-size: var(--app-text-sm);
}

.role-selector {
  display: flex;
  background: var(--app-bg-alt);
  padding: 6px;
  border-radius: 14px;
  margin-bottom: 24px;
}

.role-tab {
  flex: 1;
  text-align: center;
  padding: 12px 10px;
  font-size: var(--app-text-base);
  font-weight: 600;
  color: var(--app-text-soft);
  cursor: pointer;
  border-radius: 12px;
  text-decoration: none;
  transition: background var(--app-duration) var(--app-ease-out),
    color var(--app-duration) var(--app-ease-out),
    box-shadow var(--app-duration) var(--app-ease-out);
}

.role-tab.active {
  background: var(--app-card);
  color: var(--app-primary);
  box-shadow: var(--app-shadow-sm);
}

.login-form {
  display: grid;
  gap: 20px;
}

.form-group {
  display: grid;
  gap: 8px;
}

.form-group label {
  font-size: var(--app-text-base);
  font-weight: 600;
  color: var(--app-text-soft);
}

.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forgot-pwd {
  font-size: var(--app-text-sm);
  color: var(--app-primary);
  font-weight: 600;
}

.login-btn {
  height: 50px;
  font-size: var(--app-text-md);
  font-weight: 700;
  border-radius: 14px;
  margin-top: 4px;
}

@media (max-width: 1024px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 34px;
  }

  .brand-section {
    text-align: center;
  }

  .brand-description {
    margin: 0 auto;
  }

  .feature-list {
    max-width: 440px;
    margin: 26px auto 0;
  }

  .form-section {
    justify-content: center;
  }
}

@media (max-width: 640px) {
  .login-content {
    padding: 20px 14px;
  }

  .login-card {
    padding: 24px 18px 20px;
    border-radius: 24px;
  }

  .form-footer {
    gap: 12px;
    flex-wrap: wrap;
  }
}
</style>
