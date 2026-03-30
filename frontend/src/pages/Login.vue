<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { setRole, setToken, validateInput } from "../token";
import { useRouter } from "vue-router";
import { User, Lock, Monitor, ArrowRight } from "@element-plus/icons-vue";

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
  <div class="login-container">
    <div class="mesh-gradient"></div>
    
    <main class="login-content">
      <div class="login-shell">
        <!-- 左侧：品牌展示 -->
        <section class="brand-section">
          <div class="brand-badge">Dynamic Assessment 2.0</div>
          <h1 class="brand-title">
            释放数据价值<br />
            <span class="text-gradient">重塑评价体系</span>
          </h1>
          <p class="brand-description">
            基于知识图谱与动态行为分析，为每一位学习者构建精准的能力画像。
          </p>
          
          <div class="feature-list">
            <div class="feature-item">
              <div class="feature-icon">🎯</div>
              <div class="feature-text">
                <h3>自适应练习</h3>
                <p>根据掌握度动态调整难度</p>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">📊</div>
              <div class="feature-text">
                <h3>多维能力画像</h3>
                <p>实时反馈学习状态与瓶颈</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 右侧：登录表单 -->
        <section class="form-section">
          <div class="login-card glass-card">
            <header class="card-header">
              <h2>欢迎回来</h2>
              <p>请登录您的账号以继续</p>
            </header>

            <div class="role-selector">
              <div 
                class="role-tab" 
                :class="{ active: loginForm.role === 'student' }"
                @click="loginForm.role = 'student'"
              >
                学生登录
              </div>
              <div 
                class="role-tab" 
                :class="{ active: loginForm.role === 'admin' }"
                @click="loginForm.role = 'admin'"
              >
                教师 / 管理员
              </div>
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

            <footer class="card-footer">
              <p>系统由管理员统一分配账号</p>
              <div class="demo-account">
                <span>演示账号:</span> admin / teacher1
              </div>
            </footer>
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

/* 现代网格背景动效 */
.mesh-gradient {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(at 0% 0%, color-mix(in srgb, var(--app-primary) 15%, transparent) 0px, transparent 50%),
    radial-gradient(at 100% 0%, color-mix(in srgb, var(--app-info) 15%, transparent) 0px, transparent 50%),
    radial-gradient(at 100% 100%, color-mix(in srgb, var(--app-success) 10%, transparent) 0px, transparent 50%),
    radial-gradient(at 0% 100%, color-mix(in srgb, var(--app-warning) 10%, transparent) 0px, transparent 50%);
  filter: blur(80px);
  z-index: 0;
}

.login-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1200px;
  padding: 40px 24px;
}

.login-shell {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
}

/* 左侧样式 */
.brand-section {
  animation: slideInLeft 0.6s ease-out;
}

@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-30px); }
  to { opacity: 1; transform: translateX(0); }
}

.brand-badge {
  display: inline-block;
  padding: 6px 16px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  border-radius: 999px;
  font-size: var(--app-text-base);
  font-weight: 700;
  margin-bottom: var(--app-space-5);
}

.brand-title {
  font-size: 56px;
  line-height: 1.1;
  font-weight: 900;
  color: var(--app-text-main);
  margin-bottom: var(--app-space-5);
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
  margin-bottom: var(--app-space-8);
  max-width: 480px;
}

.feature-list {
  display: grid;
  gap: 24px;
}

.feature-item {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.feature-icon {
  width: 48px;
  height: 48px;
  background: var(--app-card);
  border-radius: var(--app-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: var(--app-shadow);
}

.feature-text h3 {
  font-size: var(--app-text-md);
  font-weight: 700;
  color: var(--app-text-main);
  margin-bottom: var(--app-space-1);
}

.feature-text p {
  font-size: var(--app-text-base);
  color: var(--app-text-soft);
}

/* 右侧样式 */
.form-section {
  display: flex;
  justify-content: flex-end;
  animation: slideInRight 0.6s ease-out;
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(30px); }
  to { opacity: 1; transform: translateX(0); }
}

.login-card {
  width: 100%;
  max-width: 440px;
  padding: 40px;
  border-radius: var(--app-radius-lg);
}

.card-header {
  margin-bottom: var(--app-space-6);
  text-align: center;
}

.card-header h2 {
  font-size: 28px;
  font-weight: 800;
  color: var(--app-text-main);
  margin-bottom: var(--app-space-2);
}

.card-header p {
  color: var(--app-text-soft);
  font-size: var(--app-text-sm);
}

.role-selector {
  display: flex;
  background: var(--app-bg-alt);
  padding: var(--app-space-1);
  border-radius: var(--app-radius-sm);
  margin-bottom: var(--app-space-6);
}

.role-tab {
  flex: 1;
  text-align: center;
  padding: 10px;
  font-size: var(--app-text-base);
  font-weight: 600;
  color: var(--app-text-soft);
  cursor: pointer;
  border-radius: var(--app-radius-sm);
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
  gap: 24px;
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
  font-size: var(--app-text-base);
  color: var(--app-primary);
  font-weight: 600;
}

.login-btn {
  height: 52px;
  font-size: var(--app-text-md);
  font-weight: 700;
  border-radius: var(--app-radius-sm);
  margin-top: var(--app-space-2);
}

.card-footer {
  margin-top: var(--app-space-6);
  text-align: center;
  padding-top: var(--app-space-5);
  border-top: 1px solid var(--app-bg-alt);
}

.card-footer p {
  font-size: var(--app-text-sm);
  color: var(--app-text-light);
  margin-bottom: var(--app-space-2);
}

.demo-account {
  font-size: var(--app-text-xs);
  color: var(--app-text-soft);
  background: var(--app-bg);
  padding: 6px var(--app-space-3);
  border-radius: var(--app-radius-sm);
  display: inline-block;
}

.demo-account span {
  font-weight: 700;
}

@media (max-width: 1024px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 60px;
  }
  
  .brand-section {
    text-align: center;
  }
  
  .brand-description {
    margin: 0 auto 48px;
  }
  
  .feature-list {
    justify-content: center;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }
  
  .form-section {
    justify-content: center;
  }
  
  .brand-title {
    font-size: 40px;
  }
}
</style>
