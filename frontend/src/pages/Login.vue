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

const mode = computed<"student" | "staff">(() => (route.path === "/login/staff" ? "staff" : "student"));

const loginForm = reactive({
  username: "",
  password: "",
  remember: true,
});

const loginAccountLabel = computed(() => (mode.value === "student" ? "学号" : "工号 / 账号"));
const loginAccountPlaceholder = computed(() =>
  mode.value === "student" ? "请输入学生学号" : "请输入教师或管理员账号",
);

const cardTitle = computed(() => (mode.value === "student" ? "学生登录" : "教师 / 管理员登录"));
const cardSubtitle = computed(() => (mode.value === "student" ? "查看学习任务、报告和反馈。" : "进入课程、评价和学生分析。"));

const sideHighlights = computed(() =>
  mode.value === "student"
    ? [
        { title: "学习更清晰", text: "任务、图谱和报告集中查看。" },
        { title: "反馈更直接", text: "阶段变化和建议一目了然。" },
      ]
    : [
        { title: "入口更集中", text: "课程、评价和分析统一进入。" },
        { title: "操作更顺手", text: "教学与管理在同一工作台完成。" },
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
        <span class="login-hero__badge">{{ mode === "student" ? "学生入口" : "教师 / 管理入口" }}</span>
        <h1>{{ mode === "student" ? "学生登录" : "教师 / 管理员登录" }}</h1>
        <p class="login-hero__lead">
          {{ mode === "student" ? "进入学习空间，继续当前任务。" : "进入工作台，处理课程与评价。" }}
        </p>

        <div class="login-hero__summary">
          <span>当前入口</span>
          <strong>{{ mode === "student" ? "学生学习空间" : "教师 / 管理工作台" }}</strong>
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
            <span class="login-card__eyebrow">欢迎回来</span>
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
              教师 / 管理端
            </router-link>
          </div>

          <form class="login-form" @submit.prevent="submitLogin">
            <div class="form-group">
              <label>{{ loginAccountLabel }}</label>
              <el-input v-model="loginForm.username" :placeholder="loginAccountPlaceholder" :prefix-icon="User" />
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
    radial-gradient(circle at top left, rgba(191, 221, 254, 0.34), transparent 24%),
    radial-gradient(circle at bottom right, rgba(255, 221, 184, 0.28), transparent 22%),
    linear-gradient(180deg, #fff7ef 0%, #fbf7f1 100%);
}

.login-page__mesh {
  position: absolute;
  inset: 0;
  pointer-events: none;
  filter: blur(24px);
  background:
    radial-gradient(circle at 0% 0%, rgba(201, 237, 255, 0.42), transparent 30%),
    radial-gradient(circle at 100% 0%, rgba(223, 246, 184, 0.22), transparent 24%),
    radial-gradient(circle at 100% 100%, rgba(255, 216, 207, 0.3), transparent 22%);
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
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
}

.login-hero {
  padding: 38px;
  display: grid;
  align-content: center;
  gap: 20px;
  background:
    radial-gradient(circle at top left, rgba(219, 234, 254, 0.3), transparent 26%),
    radial-gradient(circle at right center, rgba(220, 252, 231, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.login-hero__badge,
.login-card__eyebrow {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(34, 197, 94, 0.18);
  background: #eefbf3;
  color: #166534;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.login-hero h1 {
  margin: 0;
  max-width: 8ch;
  font-size: clamp(42px, 5vw, 64px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  color: #1f2937;
}

.login-hero__lead,
.login-hero__summary p,
.login-hero__card p,
.login-card__header p {
  margin: 0;
  color: #5f6777;
  line-height: 1.8;
}

.login-hero__summary {
  padding: 22px;
  display: grid;
  gap: 8px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
  background: rgba(255, 255, 255, 0.84);
}

.login-hero__summary span {
  font-size: 12px;
  font-weight: 800;
  color: #5f75a3;
}

.login-hero__summary strong {
  font-size: 26px;
  line-height: 1.15;
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
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
  background: rgba(255, 255, 255, 0.88);
}

.login-hero__card strong,
.login-card__header h2 {
  margin: 0;
  font-size: 22px;
  line-height: 1.2;
  color: #1f2937;
}

.login-form-wrap {
  display: grid;
}

.login-card {
  padding: 34px 30px;
  display: grid;
  gap: 24px;
}

.login-card__header,
.login-form,
.form-group {
  display: grid;
  gap: 10px;
}

.role-selector {
  display: inline-flex;
  width: fit-content;
  gap: 10px;
  align-items: center;
}

.role-tab {
  min-height: 34px;
  min-width: 96px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #eff6ff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
  color: #405266;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.role-tab.active {
  background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
}

.form-group label {
  font-size: 13px;
  font-weight: 700;
  color: #364152;
}

.form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.login-link {
  color: #4f6c8d;
  font-weight: 700;
  text-decoration: none;
}

.login-submit {
  width: 100%;
  margin-top: 6px;
}

@media (max-width: 980px) {
  .login-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 14px;
  }

  .login-hero,
  .login-card {
    padding: 22px 18px;
  }

  .login-hero__grid,
  .role-selector {
    grid-template-columns: 1fr;
  }

  .role-selector {
    display: grid;
    width: 100%;
  }

  .role-tab {
    width: 100%;
  }

  .form-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
