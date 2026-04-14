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
  mode.value === "student" ? "请输入学号" : "请输入教师或管理员账号",
);

const cardTitle = computed(() =>
  mode.value === "student" ? "学生登录" : "教师 / 管理员登录",
);
const cardSubtitle = computed(() =>
  mode.value === "student"
    ? "进入学习中心，查看当前任务、图谱与学习报告。"
    : "进入教学与管理工作台，维护课程、评价流程与平台配置。",
);

const sideHighlights = computed(() =>
  mode.value === "student"
    ? [
        { title: "继续当前任务", text: "从首页 Hero 直接回到当前知识点与推荐行动。" },
        { title: "统一学习模块", text: "学习报告、图谱和问卷保留原有能力，但视觉更统一。" },
      ]
    : [
        { title: "教学工作台", text: "课程运行、阶段评价、学生分析和审核流程共用同一壳层。" },
        { title: "管理视角", text: "平台配置、课程管理与审计模块切换更清晰。" },
      ],
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
  <div class="login-page">
    <div class="login-page__mesh"></div>

    <main class="login-shell">
      <section class="login-hero">
        <div class="login-hero__badge">{{ mode === "student" ? "学生入口" : "教师 / 管理入口" }}</div>
        <h1>教育平台的统一入口。</h1>
        <p class="login-hero__lead">
          保留现有登录逻辑与角色权限，只调整入口布局和视觉语言，让登录页和首页属于同一套产品系统。
        </p>

        <div class="login-hero__summary panel-card">
          <span>当前入口</span>
          <strong>{{ mode === "student" ? "学生学习中心" : "教师 / 管理后台" }}</strong>
          <p>{{ cardSubtitle }}</p>
        </div>

        <div class="login-hero__grid">
          <article v-for="item in sideHighlights" :key="item.title" class="login-hero__card">
            <strong>{{ item.title }}</strong>
            <p>{{ item.text }}</p>
          </article>
        </div>
      </section>

      <section class="login-form-wrap">
        <div class="login-card">
          <header class="login-card__header">
            <div class="login-card__eyebrow">欢迎回来</div>
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
              学生端
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
              <el-checkbox v-model="loginForm.remember">记住登录状态</el-checkbox>
              <router-link to="/start" class="login-link">返回首页</router-link>
            </div>

            <el-button type="primary" class="login-submit" :loading="loading" native-type="submit">
              立即登录
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </form>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  padding: 20px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(180, 224, 255, 0.3), transparent 22%),
    radial-gradient(circle at bottom right, rgba(178, 232, 220, 0.24), transparent 20%),
    #f9f1e8;
}

.login-page__mesh {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 0% 0%, rgba(201, 237, 255, 0.42), transparent 30%),
    radial-gradient(circle at 100% 0%, rgba(185, 247, 176, 0.18), transparent 30%),
    radial-gradient(circle at 100% 100%, rgba(255, 216, 207, 0.28), transparent 24%);
  filter: blur(22px);
  pointer-events: none;
}

.login-shell {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
  min-height: calc(100vh - 40px);
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
  gap: 28px;
  align-items: stretch;
}

.login-hero,
.login-card {
  border-radius: 30px;
  border: 3px solid #1d2433;
  box-shadow: 8px 8px 0 #1d2433;
  background: rgba(255, 255, 255, 0.94);
}

.login-hero {
  padding: 38px;
  display: grid;
  align-content: center;
  gap: 20px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.5), transparent 28%),
    linear-gradient(180deg, #fffdfa 0%, #f8fbff 100%);
}

.login-hero__badge,
.login-card__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 8px 14px;
  border-radius: 999px;
  background: #c9ffb9;
  color: #1d2433;
  border: 2px solid #1d2433;
  box-shadow: 4px 4px 0 #1d2433;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.login-hero h1 {
  margin: 0;
  max-width: 11ch;
  font-size: clamp(42px, 5vw, 64px);
  line-height: 1.02;
  color: #1d2433;
}

.login-hero__lead {
  max-width: 56ch;
  margin: 0;
  font-size: 17px;
  line-height: 1.9;
  color: #5f6777;
}

.login-hero__summary {
  padding: 22px;
  display: grid;
  gap: 8px;
  border-radius: 24px;
  border: 2px solid #1d2433;
  background: linear-gradient(180deg, #f3f9ff 0%, #ffffff 100%);
  box-shadow: 6px 6px 0 rgba(29, 36, 51, 0.12);
}

.login-hero__summary span {
  font-size: 12px;
  font-weight: 800;
  color: #5f75a3;
}

.login-hero__summary strong {
  font-size: 26px;
  line-height: 1.15;
  color: #1d2433;
}

.login-hero__summary p,
.login-hero__card p {
  margin: 0;
  color: #5f6777;
  line-height: 1.8;
}

.login-hero__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.login-hero__card {
  display: grid;
  gap: 8px;
  padding: 20px;
  border-radius: 24px;
  border: 2px solid #1d2433;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  box-shadow: 6px 6px 0 rgba(29, 36, 51, 0.1);
}

.login-hero__card strong {
  font-size: 18px;
  color: #1d2433;
}

.login-form-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: min(100%, 520px);
  padding: 30px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.4), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.login-card__header {
  display: grid;
  gap: 10px;
  margin-bottom: 24px;
}

.login-card__header h2 {
  margin: 0;
  font-size: 32px;
  color: #1d2433;
}

.login-card__header p {
  margin: 0;
  color: #5f6777;
  line-height: 1.8;
}

.role-selector {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 8px;
  border-radius: 20px;
  border: 2px solid #1d2433;
  background: #eef8ff;
  box-shadow: 4px 4px 0 rgba(29, 36, 51, 0.1);
  margin-bottom: 24px;
}

.role-tab {
  min-height: 50px;
  padding: 0 14px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  text-decoration: none;
  color: #4a5366;
  border: 2px solid transparent;
  font-weight: 800;
  transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.role-tab.active {
  background: #ffffff;
  color: #17358f;
  border-color: #1d2433;
  box-shadow: 4px 4px 0 rgba(29, 36, 51, 0.12);
}

.role-tab:not(.active):hover {
  transform: translate(-1px, -1px);
  color: #1d2433;
}

.login-form {
  display: grid;
  gap: 18px;
}

.form-group {
  display: grid;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 800;
  color: #1d2433;
}

.form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.login-link {
  color: #17358f;
  font-weight: 800;
  text-decoration: none;
}

.login-submit {
  min-height: 54px;
  font-size: 15px;
}

:deep(.login-form .el-input__wrapper) {
  border-radius: 16px !important;
  border: 2px solid #1d2433 !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

:deep(.login-form .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 3px rgba(80, 186, 255, 0.2) !important;
}

:deep(.login-form .el-input__inner) {
  color: #1d2433 !important;
  font-weight: 600;
}

:deep(.login-form .el-checkbox__label) {
  color: #1d2433 !important;
  font-weight: 700;
}

:deep(.login-form .el-checkbox__inner) {
  border: 2px solid #1d2433 !important;
  border-radius: 6px !important;
}

:deep(.login-submit.el-button--primary) {
  border: 2px solid #1d2433 !important;
  border-radius: 16px !important;
  background: #32d25f !important;
  background-image: none !important;
  color: #10201a !important;
  box-shadow: 4px 4px 0 #1d2433 !important;
}

:deep(.login-submit.el-button--primary:hover) {
  transform: translate(-1px, -1px);
  box-shadow: 6px 6px 0 #1d2433 !important;
}

@media (max-width: 1040px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .login-hero h1 {
    max-width: none;
  }
}

@media (max-width: 760px) {
  .login-page {
    padding: 14px;
  }

  .login-hero,
  .login-card {
    padding: 22px 20px;
  }

  .login-hero__grid {
    grid-template-columns: 1fr;
  }
}
</style>
