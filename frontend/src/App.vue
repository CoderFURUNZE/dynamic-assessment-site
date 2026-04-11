<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Calendar, Expand, Fold, Monitor, SwitchButton, User } from "@element-plus/icons-vue";
import { clearToken, getRole } from "./token";
import { appNavigation, type AppNavItem } from "./layouts/appNavigation";
import { buildTeacherSubjectQuery, getSavedTeacherSubject } from "./utils/teacherCourse";

const route = useRoute();
const router = useRouter();

const sidebarCollapsed = ref(localStorage.getItem("da_sidebar_collapsed") === "1");

watch(sidebarCollapsed, (value) => {
  localStorage.setItem("da_sidebar_collapsed", value ? "1" : "0");
});

const role = computed(() => getRole() || "");
const routeGroup = computed<"admin" | "teacher" | "student" | "start" | "login">(() => {
  if (route.path.startsWith("/admin")) return "admin";
  if (route.path.startsWith("/teacher")) return "teacher";
  if (route.path.startsWith("/student")) return "student";
  if (route.path === "/start") return "start";
  if (route.path.startsWith("/login")) return "login";
  return "login";
});

const isAdmin = computed(() => role.value === "admin");
const isTeacher = computed(() => role.value === "teacher");
const isAuthPage = computed(() => routeGroup.value === "login" || routeGroup.value === "start");
const isStandaloneWorkspace = computed(() => Boolean(route.meta?.standaloneWorkspace));
const isStudentPreview = computed(
  () =>
    routeGroup.value === "student"
    && (role.value === "admin" || role.value === "teacher")
    && String(route.query.preview || "") === "1",
);
const canOpenPreview = computed(() => routeGroup.value === "admin" && isAdmin.value);
const canReturnToAdmin = computed(() => routeGroup.value === "student" && isStudentPreview.value && isAdmin.value);

const currentNavTree = computed<AppNavItem[]>(() => {
  if (routeGroup.value === "student" || routeGroup.value === "teacher" || routeGroup.value === "admin") {
    return appNavigation[routeGroup.value];
  }
  return [];
});

function parseTarget(target: string) {
  const [path, rawQuery] = target.split("?");
  const query: Record<string, string> = {};
  if (rawQuery) {
    rawQuery.split("&").forEach((entry) => {
      const [key, value] = entry.split("=");
      if (key) query[key] = value || "";
    });
  }
  return { path, query };
}

const activeNavKey = computed(() => {
  if (route.path.startsWith("/student/graph-workspace")) return "student-graph";
  if (route.path.startsWith("/student/enroll")) return "student-enroll";
  if (route.path.startsWith("/student/report")) return "student-report";
  if (route.path.startsWith("/student/questionnaire")) return "student-questionnaire";
  if (route.path.startsWith("/student/dashboard")) return "student-dashboard";

  if (route.path.startsWith("/teacher/content")) return "teacher-content";
  if (route.path.startsWith("/teacher/kp-content/")) return "teacher-content";
  if (route.path.startsWith("/teacher/resources/")) return "teacher-content";
  if (route.path.startsWith("/teacher/workspace")) return "teacher-workspace";
  if (route.path.startsWith("/teacher/evaluation")) {
    const tab = String(route.query.tab || "stages");
    if (tab === "indicators") return "teacher-evaluation-indicators";
    if (tab === "imports") return "teacher-evaluation-imports";
    if (tab === "behavior") return "teacher-evaluation-behavior";
    return "teacher-evaluation-stages";
  }
  if (route.path.startsWith("/teacher/students")) {
    const tab = String(route.query.tab || "class");
    if (tab === "detail") return "teacher-students-detail";
    if (tab === "rules") return "teacher-students-rules";
    if (tab === "results") return "teacher-students-results";
    return "teacher-students-class";
  }
  if (route.path.startsWith("/teacher/review")) {
    const tab = String(route.query.tab || "enrollment");
    if (tab === "final") return "teacher-review-final";
    return "teacher-review-enrollment";
  }

  if (route.path.startsWith("/admin/dashboard")) return "admin-dashboard";
  if (route.path.startsWith("/admin/audit")) return "admin-audit";
  if (route.path.startsWith("/admin/basic/courses")) return "admin-courses";
  if (route.path.startsWith("/admin/basic/users")) return "admin-users";
  if (route.path.startsWith("/admin/basic/teachers")) return "admin-teachers";
  if (route.path.startsWith("/admin/evaluation/dimensions")) return "admin-dimensions";
  if (route.path.startsWith("/admin/evaluation/persona/settings")) return "admin-persona-settings";
  return "";
});

const currentSection = computed(() => currentNavTree.value.find((item) => item.children?.some((child) => child.key === activeNavKey.value)) ?? null);
const currentNavItem = computed(() => currentSection.value?.children?.find((item) => item.key === activeNavKey.value) ?? null);
const currentTitleIcon = computed(() => currentNavItem.value?.icon || currentSection.value?.icon || Calendar);
const roleLabel = computed(() =>
  isStudentPreview.value
    ? "学生预览"
    : routeGroup.value === "admin"
      ? "管理员"
      : routeGroup.value === "teacher"
        ? "教师"
        : "学生",
);

const pageTitle = computed(() => {
  if (route.path.startsWith("/student/kp-content/")) return "知识点学习";
  if (route.path.startsWith("/teacher/kp-content/")) return "知识点配置工作台";
  if (route.path.startsWith("/teacher/resources/")) return "资源详情";
  return currentNavItem.value?.label || String(route.meta?.title || "当前页面");
});

const pageSection = computed(() => {
  if (route.path.startsWith("/student/kp-content/")) return "学习任务";
  if (route.path.startsWith("/teacher/kp-content/")) return "知识点配置";
  if (route.path.startsWith("/teacher/resources/")) return "课程工作台";
  return currentSection.value?.label || (routeGroup.value === "student" ? "学生端" : routeGroup.value === "teacher" ? "教师端" : routeGroup.value === "admin" ? "管理端" : "");
});

function logout() {
  clearToken();
  router.push("/login/student");
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
}

function openPreview() {
  router.push({ path: "/student/dashboard", query: { ...route.query, preview: "1" } });
}

function returnToAdmin() {
  router.push("/admin/dashboard");
}

function navigateTo(target: string) {
  const { path, query } = parseTarget(target);
  const preview = String(route.query.preview || "");
  const lastStudentSubject = (localStorage.getItem("da_student_last_subject") || "").trim();

  if (routeGroup.value === "student" && path.startsWith("/student")) {
    const nextQuery: Record<string, string> = { ...query };
    if (path !== "/student/enroll" && lastStudentSubject && !nextQuery.subject) nextQuery.subject = lastStudentSubject;
    if (preview === "1") nextQuery.preview = "1";
    router.push({ path, query: { ...route.query, ...nextQuery } });
    return;
  }

  if (routeGroup.value === "teacher" && path.startsWith("/teacher")) {
    const subject = String(route.query.subject || getSavedTeacherSubject() || "");
    router.push({ path, query: { ...buildTeacherSubjectQuery(subject), ...query } });
    return;
  }

  router.push({ path, query });
}

function goBackToMain() {
  if (routeGroup.value === "student") {
    router.push({ path: "/student/dashboard", query: { ...route.query } });
    return;
  }
  if (routeGroup.value === "teacher") {
    router.push({ path: "/teacher/workspace", query: { ...route.query } });
  }
}
</script>

<template>
  <div
    class="pro-shell"
    :class="{
      'pro-shell--auth': isAuthPage,
      'pro-shell--standalone': isStandaloneWorkspace,
      'pro-shell--collapsed': sidebarCollapsed,
    }"
  >
    <template v-if="isStandaloneWorkspace">
      <main class="pro-standalone">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </template>

    <template v-else-if="isAuthPage">
      <main class="pro-auth">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </template>

    <template v-else>
      <aside class="pro-sider">
        <div class="pro-brand" @click="router.push('/')">
          <div class="pro-brand__logo">DA</div>
          <div v-if="!sidebarCollapsed" class="pro-brand__text">
            <strong>动态评价系统</strong>
            <span>{{ routeGroup === "student" ? "学生学习后台" : routeGroup === "teacher" ? "教师工作后台" : "平台管理后台" }}</span>
          </div>
        </div>

        <nav class="pro-menu">
          <section v-for="section in currentNavTree" :key="section.key" class="pro-menu__section">
            <div v-if="section.children && !sidebarCollapsed" class="pro-menu__children">
              <button
                v-for="item in section.children"
                :key="item.key"
                class="pro-menu__item pro-menu__item--child"
                :class="{ active: activeNavKey === item.key }"
                @click="navigateTo(item.path)"
              >
                <el-icon v-if="item.icon" class="pro-menu__child-icon"><component :is="item.icon" /></el-icon>
                <span>{{ item.label }}</span>
              </button>
            </div>
          </section>
        </nav>
      </aside>

      <section class="pro-main">
        <header class="pro-header">
          <div class="pro-header__left">
            <button class="pro-icon-btn" @click="toggleSidebar">
              <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
            </button>
            <div class="pro-header__badge">
              <el-icon><component :is="currentTitleIcon" /></el-icon>
            </div>
            <div class="pro-header__title">
              <strong>{{ pageTitle }}</strong>
            </div>
          </div>

          <div class="pro-header__right">
            <div class="pro-role-chip">
              <span class="pro-role-chip__dot"></span>
              <span>{{ roleLabel }}</span>
            </div>

            <el-tooltip v-if="canOpenPreview" content="预览学生端" placement="bottom">
              <button class="pro-icon-btn" @click="openPreview">
                <el-icon><Monitor /></el-icon>
              </button>
            </el-tooltip>

            <el-tooltip v-if="canReturnToAdmin" content="返回管理员端" placement="bottom">
              <button class="pro-icon-btn" @click="returnToAdmin">
                <el-icon><ArrowLeft /></el-icon>
              </button>
            </el-tooltip>

            <el-tooltip content="账号菜单" placement="bottom">
              <el-dropdown trigger="click">
                <button class="pro-icon-btn">
                  <el-icon><User /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="logout" :icon="SwitchButton">退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </el-tooltip>
          </div>
        </header>

        <div class="pro-content">
          <router-view v-slot="{ Component }">
            <transition name="page-fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </section>
    </template>

    <button v-if="isStandaloneWorkspace" class="pro-standalone-back" @click="goBackToMain">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回主工作台</span>
    </button>
  </div>
</template>

<style scoped>
.pro-shell {
  min-height: 100vh;
  background: var(--app-gradient-page);
}

.pro-shell--standalone {
  min-height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
}

.pro-auth,
.pro-standalone {
  min-height: 100vh;
}

.pro-standalone {
  height: 100dvh;
  overflow: hidden;
}

.pro-sider {
  position: fixed;
  inset: 0 auto 0 0;
  width: 220px;
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  background:
    radial-gradient(circle at top left, rgba(111, 182, 255, 0.26), transparent 22%),
    radial-gradient(circle at bottom left, rgba(88, 146, 255, 0.14), transparent 28%),
    linear-gradient(180deg, #10233a 0%, #173451 54%, #21486d 100%);
  color: #d7e4f5;
  box-shadow: 18px 0 40px rgba(15, 34, 62, 0.16);
  z-index: 1100;
  transition: width 0.22s ease;
}

.pro-shell--collapsed .pro-sider {
  width: 88px;
}

.pro-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px 18px;
  margin-bottom: 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.pro-brand__logo {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #4a84ff 0%, #6bc5ff 100%);
  color: #fff;
  font-weight: 800;
  box-shadow: 0 16px 28px rgba(74, 132, 255, 0.28);
}

.pro-brand__text {
  display: grid;
  gap: 2px;
}

.pro-brand__text strong {
  font-size: 16px;
  color: #fff;
}

.pro-brand__text span {
  font-size: 12px;
  color: rgba(215, 228, 245, 0.72);
}

.pro-menu {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.pro-menu__section {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: none;
}

.pro-menu__children {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  justify-items: center;
}

.pro-menu__item {
  min-height: 42px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: rgba(215, 228, 245, 0.82);
  cursor: pointer;
  transition: all 0.2s ease;
}

.pro-menu__item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.pro-menu__item.active {
  background: linear-gradient(90deg, rgba(74, 132, 255, 0.28) 0%, rgba(107, 197, 255, 0.18) 100%);
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(162, 205, 255, 0.22);
}

.pro-menu__item--child {
  width: calc(100% - 28px);
  min-height: 44px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.pro-menu__icon {
  font-size: 16px;
}

.pro-menu__child-icon {
  font-size: 14px;
  opacity: 0.9;
}

.pro-main {
  min-height: 100vh;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.22s ease;
}

.pro-shell--collapsed .pro-main {
  margin-left: 88px;
}

.pro-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 251, 255, 0.94) 100%);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(211, 223, 242, 0.9);
  box-shadow: 0 8px 24px rgba(87, 116, 166, 0.07);
}

.pro-header__left,
.pro-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pro-header__title {
  display: flex;
  align-items: center;
}

.pro-header__title strong {
  font-size: 20px;
  line-height: 1.2;
  color: #1f2d3d;
}

.pro-header__badge {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(204, 220, 245, 0.95);
  background: linear-gradient(135deg, rgba(72, 127, 245, 0.12) 0%, rgba(111, 193, 255, 0.14) 100%);
  color: #3268da;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.76);
}

.pro-icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(211, 223, 242, 0.95);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 248, 255, 0.98) 100%);
  color: #526274;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pro-icon-btn:hover {
  border-color: rgba(144, 175, 230, 0.95);
  background: linear-gradient(180deg, rgba(255, 255, 255, 1) 0%, rgba(237, 243, 255, 1) 100%);
  color: #2f5ea4;
}

.pro-role-chip {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(211, 223, 242, 0.95);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 248, 255, 0.98) 100%);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #4f6278;
}

.pro-role-chip__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(135deg, #4a84ff 0%, #6bc5ff 100%);
  box-shadow: 0 0 0 5px rgba(74, 132, 255, 0.12);
}

.pro-content {
  flex: 1;
  min-height: 0;
  padding: 24px;
  overflow: auto;
  background: radial-gradient(circle at top right, rgba(111, 193, 255, 0.08), transparent 24%), transparent;
}

.pro-standalone-back {
  position: fixed;
  left: 20px;
  top: 16px;
  z-index: 1400;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid rgba(211, 223, 242, 0.95);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(244, 248, 255, 0.96) 100%);
  color: #31455f;
  box-shadow: 0 12px 28px rgba(87, 116, 166, 0.16);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

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

@media (max-width: 1100px) {
  .pro-sider {
    width: 88px;
  }

  .pro-main {
    margin-left: 88px;
  }

  .pro-brand__text,
  .pro-menu__children,
  .pro-menu__section-text {
    display: none;
  }
}

@media (max-width: 760px) {
  .pro-header {
    height: auto;
    min-height: 72px;
    padding: 14px 16px;
    align-items: flex-start;
    flex-direction: column;
  }

  .pro-content {
    padding: 16px;
  }
}
</style>
