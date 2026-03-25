<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearToken, getRole, getToken } from "./token";
import { isLoading } from "./loading";
import { buildTeacherSubjectQuery, getSavedTeacherSubject } from "./utils/teacherCourse";

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
  if (routeGroup.value === "teacher" && path.startsWith("/teacher")) {
    const subject = String(route.query.subject || getSavedTeacherSubject() || "");
    router.push({ path, query: buildTeacherSubjectQuery(subject) });
    return;
  }
  router.push(path);
}
</script>

<template>
  <el-container class="app-shell" :class="{ 'login-container': isAuthPage }">
    <el-header v-if="!isAuthPage" class="app-header">
      <div class="app-header__main">
        <div class="app-brand">动态评价系统</div>
        <div class="app-header__meta">选课程，看图谱，学内容，看结果</div>
      </div>
      <nav v-if="navItems.length" class="app-nav">
        <button
          v-for="item in navItems"
          :key="item.path"
          class="app-nav__item"
          :class="{ 'app-nav__item--active': isNavActive(item.path) }"
          @click="navigateTo(item.path)"
        >
          {{ item.label }}
        </button>
      </nav>
      <div class="app-menu-label" :class="`app-menu-label--${routeGroup}`">
        {{ routeGroup === "admin" ? "管理端" : routeGroup === "teacher" ? "教师工作台" : "学习中心" }}
      </div>
      <div class="app-header__actions">
        <el-button v-if="(routeGroup === 'admin' && isAdmin) || (routeGroup === 'teacher' && isTeacher)" size="small" @click="router.push('/student/overview')">
          学习者端预览
        </el-button>
        <el-button v-if="getToken()" type="default" @click="logout">退出</el-button>
      </div>
    </el-header>

    <template v-if="!isAuthPage">
      <el-main class="app-main">
        <router-view />
      </el-main>
    </template>
    <template v-else>
      <router-view />
    </template>

    <div v-if="isLoading" class="global-loading-mask">加载中...</div>
  </el-container>
</template>

<style>
.login-container {
  display: block;
  height: 100vh;
  overflow: hidden;
  margin: 0;
  padding: 0;
}

.global-loading-mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(18, 31, 51, 0.2);
  color: #fff;
  z-index: 3000;
  font-size: 15px;
  font-weight: 700;
  backdrop-filter: blur(6px);
}

.app-header__main {
  display: grid;
  gap: 4px;
  min-width: 220px;
}

.app-header__meta {
  font-size: 12px;
  color: var(--app-ink-soft);
  letter-spacing: 0.02em;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.app-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  padding: 2px 0;
}

.app-nav__item {
  min-height: 38px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.6);
  color: var(--app-ink-soft);
  border-radius: 999px;
  padding: 0 14px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.app-nav__item:hover {
  background: #ffffff;
  color: var(--app-ink);
}

.app-nav__item--active {
  border-color: #d7e1ed;
  background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%);
  color: var(--app-ink);
  box-shadow: var(--app-shadow-soft);
}

.app-menu-label {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  background: #ffffff;
  color: #62758f;
  font-weight: 700;
  font-size: 12px;
  border: 1px solid var(--app-border);
  display: inline-flex;
  align-items: center;
}

.app-menu-label--admin {
  background: #f7f9fc;
}

.app-menu-label--teacher {
  background: #f7faf8;
  color: #587a66;
  border-color: #dcebe4;
}

.app-menu-label--student {
  background: #f7f9fc;
  color: #62758f;
}

@media (max-width: 900px) {
  .app-header__main {
    width: 100%;
  }

  .app-nav {
    width: 100%;
    order: 4;
  }

  .app-header__actions {
    width: 100%;
  }
}
</style>
