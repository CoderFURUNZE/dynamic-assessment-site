<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearToken, getRole, getToken } from "./token";
import { isLoading } from "./loading";
import { buildTeacherSubjectQuery, getSavedTeacherSubject } from "./utils/teacherCourse";
import { Monitor, SwitchButton, User } from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();

const role = computed(() => getRole() || "");
const isAdmin = computed(() => role.value === "admin");
const isTeacher = computed(() => role.value === "teacher");
const routeGroup = computed<"admin" | "teacher" | "student" | "start" | "login">(() => {
  if (route.path.startsWith("/admin")) return "admin";
  if (route.path.startsWith("/teacher")) return "teacher";
  if (route.path.startsWith("/student")) return "student";
  if (route.path === "/start") return "start";
  return "login";
});
const isStudentPreview = computed(
  () =>
    routeGroup.value === "student"
    && (role.value === "admin" || role.value === "teacher")
    && String(route.query.preview || "") === "1",
);

const isAuthPage = computed(() => routeGroup.value === "login" || routeGroup.value === "start");
const navItems = computed(() => {
  if (routeGroup.value === "student") {
    return [
      { label: "首页", path: "/student/overview" },
      { label: "图谱", path: "/student/graph-workspace" },
      { label: "报告", path: "/student/report" },
      { label: "问卷", path: "/student/questionnaire" },
    ];
  }
  if (routeGroup.value === "teacher") {
    return [
      { label: "课程", path: "/teacher/courses" },
      { label: "图谱", path: "/teacher/graph-workspace" },
      { label: "导入", path: "/teacher/imports" },
      { label: "学生", path: "/teacher/students" },
      { label: "评分", path: "/teacher/final-review" },
    ];
  }
  if (routeGroup.value === "admin") {
    return [
      { label: "概览", path: "/admin/dashboard" },
      { label: "课程", path: "/admin/courses" },
      { label: "用户", path: "/admin/users" },
      { label: "规则", path: "/admin/persona" },
      { label: "指标", path: "/admin/dimensions" },
    ];
  }
  return [];
});

function logout() {
  clearToken();
  router.push("/login");
}

function isNavActive(path: string) {
  return route.path === path;
}

function navigateTo(path: string) {
  const preview = String(route.query.preview || "");
  const lastStudentSubject = (localStorage.getItem("da_student_last_subject") || "").trim();

  if (routeGroup.value === "student" && path === "/student/graph-workspace") {
    const q: Record<string, string> = {};
    if (lastStudentSubject) q.subject = lastStudentSubject;
    if (preview === "1") q.preview = "1";
    router.push({ path, query: { ...route.query, ...q } });
    return;
  }
  if (routeGroup.value === "student" && preview === "1" && path.startsWith("/student")) {
    router.push({ path, query: { ...route.query, preview: "1" } });
    return;
  }
  if (routeGroup.value === "teacher" && path.startsWith("/teacher")) {
    const subject = String(route.query.subject || getSavedTeacherSubject() || "");
    router.push({ path, query: { ...route.query, ...buildTeacherSubjectQuery(subject) } });
    return;
  }
  router.push(path);
}
</script>

<template>
  <div class="app-root" :class="{ 'is-auth': isAuthPage }">
    <!-- 顶部导航 -->
    <header v-if="!isAuthPage" class="global-header glass-card">
      <div class="header-content">
        <!-- Logo -->
        <div class="header-left">
          <div class="logo-wrapper" @click="router.push('/')">
            <div class="logo-icon"></div>
            <div class="logo-text">
              <span class="name">动态评价系统</span>
              <span class="tag">DYNAMIC ASSESSMENT</span>
            </div>
          </div>
        </div>

        <!-- 导航项 -->
        <nav class="header-center">
          <div class="nav-pills">
            <button
              v-for="item in navItems"
              :key="item.path"
              class="nav-pill"
              :class="{ active: isNavActive(item.path) }"
              @click="navigateTo(item.path)"
            >
              {{ item.label }}
            </button>
          </div>
        </nav>

        <!-- 用户操作 -->
        <div class="header-right">
          <div class="user-profile">
            <div class="role-tag" :class="routeGroup">
              {{
                isStudentPreview
                  ? "预览模式"
                  : routeGroup === "admin"
                    ? "管理员"
                    : routeGroup === "teacher"
                      ? "教师"
                      : "学生"
              }}
            </div>
            
            <div class="action-buttons">
              <el-tooltip v-if="(routeGroup === 'admin' && isAdmin) || (routeGroup === 'teacher' && isTeacher)" content="预览学生端" placement="bottom">
                <button class="icon-btn" @click="router.push({ path: '/student/overview', query: { ...route.query, preview: '1' } })">
                  <el-icon><Monitor /></el-icon>
                </button>
              </el-tooltip>
              
              <el-dropdown trigger="click">
                <button class="icon-btn profile-trigger">
                  <el-icon><User /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="logout" :icon="SwitchButton">退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="global-main" :class="{ 'has-header': !isAuthPage }">
      <div class="main-content-wrapper">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- 全局加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <span>正在处理中...</span>
    </div>
  </div>
</template>

<style>
/* 全局布局样式 */
.app-root {
  flex: 1 0 auto;
  width: 100%;
  max-width: 100vw;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: visible;
}

.global-header {
  position: absolute; /* 改为绝对定位以更好控制流 */
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 48px);
  max-width: 1400px;
  height: 64px;
  z-index: 1000;
  border-radius: var(--app-radius-lg);
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.header-content {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  row-gap: 10px;
}

/* Logo 样式 */
.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: var(--app-gradient-primary);
  border-radius: var(--app-radius-sm);
  box-shadow: 0 4px 10px rgba(79, 140, 255, 0.3);
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-text .name {
  font-size: var(--app-text-md);
  font-weight: 800;
  color: var(--app-text-main);
  line-height: 1.2;
}

.logo-text .tag {
  font-size: 9px;
  font-weight: 700;
  color: var(--app-text-light);
  letter-spacing: 0.1em;
}

/* 导航药丸样式 */
.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-pills {
  display: flex;
  gap: var(--app-space-1);
  background: color-mix(in srgb, var(--app-text-main) 5%, transparent);
  padding: var(--app-space-1);
  border-radius: 14px;
}

.nav-pill {
  padding: var(--app-space-2) 18px;
  border: none;
  background: transparent;
  color: var(--app-text-soft);
  font-size: var(--app-text-base);
  font-weight: 600;
  border-radius: var(--app-radius-sm);
  cursor: pointer;
  transition: color var(--app-duration) var(--app-ease-out),
    background var(--app-duration) var(--app-ease-out),
    box-shadow var(--app-duration) var(--app-ease-out);
}

.nav-pill:hover {
  color: var(--app-primary);
}

.nav-pill.active {
  background: var(--app-card);
  color: var(--app-primary);
  box-shadow: var(--app-shadow-sm);
}

/* 右侧用户区域 */
.header-right {
  display: flex;
  align-items: center;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 16px;
}

.role-tag {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.role-tag.admin { background: color-mix(in srgb, var(--app-error) 12%, white); color: var(--app-error); }
.role-tag.teacher { background: color-mix(in srgb, var(--app-success) 14%, white); color: var(--app-success); }
.role-tag.student { background: var(--app-primary-soft); color: var(--app-primary); }

.action-buttons {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: var(--app-card);
  border: 1px solid var(--app-border-hover);
  border-radius: var(--app-radius-sm);
  color: var(--app-text-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: color var(--app-duration) var(--app-ease-out),
    border-color var(--app-duration) var(--app-ease-out),
    background var(--app-duration) var(--app-ease-out);
}

.icon-btn:hover {
  color: var(--app-primary);
  border-color: var(--app-primary);
  background: var(--app-primary-soft);
}

/* 主体区域 */
.global-main {
  flex: 1 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: visible;
}

.global-main.has-header {
  padding-top: 96px; /* 留出 header 空间 + 间距 */
  padding-bottom: var(--app-space-5);
}

/* 页面内容随高度伸展，由 app-root 统一纵向滚动 */
.main-content-wrapper {
  flex: 1 0 auto;
  overflow: visible;
  display: flex;
  flex-direction: column;
}

/* 过渡动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity var(--app-duration-slow) var(--app-ease-out),
    transform var(--app-duration-slow) var(--app-ease-out);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 加载遮罩 */
.loading-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: color-mix(in srgb, var(--app-card) 82%, transparent);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--app-space-4);
  color: var(--app-primary);
  font-weight: 600;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--app-primary-tint);
  border-top-color: var(--app-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1024px) {
  .global-header {
    width: calc(100% - 24px);
    top: 12px;
    height: auto;
    min-height: 64px;
    padding-top: 10px;
    padding-bottom: 10px;
  }
  .header-center {
    order: 3;
    flex: 1 1 100%;
    justify-content: flex-start;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    padding-bottom: 2px;
  }
  .nav-pills {
    flex-wrap: nowrap;
    width: max-content;
    max-width: 100%;
  }
}
</style>
