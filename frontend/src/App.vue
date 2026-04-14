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

const studentNavItems = computed<AppNavItem[]>(() =>
  routeGroup.value === "student"
    ? currentNavTree.value.flatMap((section) => section.children ?? [])
    : [],
);

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
      'pro-shell--student': routeGroup === 'student',
      'pro-shell--teacher': routeGroup === 'teacher',
      'pro-shell--admin': routeGroup === 'admin',
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

    <template v-else-if="routeGroup === 'student'">
      <section class="student-shell">
        <header class="student-shell__header">
          <div class="student-shell__brand" @click="router.push('/student/dashboard')">
            <div class="student-shell__logo">DA</div>
            <div class="student-shell__brand-copy">
              <strong>动态评价系统</strong>
              <span>Student Learning Space</span>
            </div>
          </div>

          <nav class="student-shell__nav">
            <button
              v-for="item in studentNavItems"
              :key="item.key"
              class="student-shell__nav-item"
              :class="{ active: activeNavKey === item.key }"
              @click="navigateTo(item.path)"
            >
              {{ item.label }}
            </button>
          </nav>

          <div class="student-shell__actions">
            <div class="pro-role-chip">
              <span class="pro-role-chip__dot"></span>
              <span>{{ roleLabel }}</span>
            </div>

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

        <main class="student-shell__content">
          <router-view v-slot="{ Component }">
            <transition name="page-fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </section>
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
              <span>{{ pageSection }}</span>
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

.pro-shell--student {
  background:
    radial-gradient(circle at top left, rgba(180, 224, 255, 0.26), transparent 20%),
    radial-gradient(circle at bottom right, rgba(178, 232, 220, 0.18), transparent 22%),
    #f9f1e8;
}

.pro-shell--teacher {
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.14), transparent 22%),
    radial-gradient(circle at bottom right, rgba(245, 158, 11, 0.08), transparent 18%),
    linear-gradient(180deg, #eef4ff 0%, #f7faff 100%);
}

.pro-shell--admin {
  background:
    radial-gradient(circle at top left, rgba(124, 58, 237, 0.12), transparent 22%),
    radial-gradient(circle at bottom right, rgba(99, 102, 241, 0.1), transparent 18%),
    linear-gradient(180deg, #f5f3ff 0%, #faf7ff 100%);
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

.student-shell {
  max-width: 1240px;
  margin: 0 auto;
  padding: 18px 18px 28px;
}

.student-shell__header {
  position: sticky;
  top: 14px;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 18px;
  border-radius: 28px;
  background: rgba(255, 253, 249, 0.92);
  border: 3px solid #1f2937;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.student-shell__brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.student-shell__logo {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: #ffd8cf;
  border: 1.5px solid #c6d8ef;
  font-family: "Fredoka", "Nunito", sans-serif;
  font-weight: 700;
  color: #1d2433;
}

.student-shell__brand-copy {
  display: grid;
}

.student-shell__brand-copy strong {
  color: #1d2433;
  font-family: "Fredoka", "Nunito", sans-serif;
  font-size: 16px;
}

.student-shell__brand-copy span {
  color: #6d7483;
  font-size: 11px;
}

.student-shell__nav {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.student-shell__nav-item {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: #ffffff;
  font: inherit;
  font-weight: 800;
  color: #445f7e;
  cursor: pointer;
}

.student-shell__nav-item.active {
  background: #eaf8d3;
  color: #16355c;
}

.student-shell__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-shell__content {
  padding-top: 20px;
}

.pro-standalone {
  height: 100dvh;
  overflow: hidden;
}

.pro-sider {
  position: fixed;
  inset: 14px auto 14px 14px;
  width: 220px;
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  background:
    radial-gradient(circle at top left, rgba(96, 165, 250, 0.24), transparent 24%),
    radial-gradient(circle at bottom left, rgba(34, 197, 94, 0.14), transparent 28%),
    linear-gradient(180deg, #0f1f40 0%, #173269 54%, #1d4d8f 100%);
  color: #d9e6fb;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 28px;
  box-shadow: 0 24px 54px rgba(15, 23, 42, 0.2);
  z-index: 1100;
  transition: width 0.22s ease, inset 0.22s ease;
}

.pro-shell--student .pro-sider {
  background: #fffdf9;
  color: #1d2433;
  border: 2px solid #1d2433;
  box-shadow: 8px 8px 0 #1d2433;
}

.pro-shell--student .pro-brand {
  border-bottom-color: rgba(29, 36, 51, 0.12);
}

.pro-shell--student .pro-brand__logo {
  background: #ffd8cf;
  color: #1d2433;
  border: 1.5px solid #1d2433;
  box-shadow: 4px 4px 0 #1d2433;
}

.pro-shell--student .pro-brand__text strong {
  color: #1d2433;
  font-family: "Fredoka", "Nunito", sans-serif;
}

.pro-shell--student .pro-brand__text span {
  color: #6d7483;
}

.pro-shell--collapsed .pro-sider {
  width: 88px;
}

.pro-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 10px 18px;
  margin-bottom: 18px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.pro-brand__logo {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #ffffff 0%, #dbeafe 100%);
  color: var(--app-primary-deep);
  font-weight: 800;
  box-shadow: 0 18px 28px rgba(15, 23, 42, 0.18);
}

.pro-brand__text {
  display: grid;
  gap: 2px;
}

.pro-brand__text strong {
  font-size: 17px;
  color: #fff;
}

.pro-brand__text span {
  font-size: 12px;
  color: rgba(217, 230, 251, 0.72);
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
  margin-bottom: 16px;
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
  min-height: 44px;
  border: 0;
  border-radius: 16px;
  background: transparent;
  color: rgba(217, 230, 251, 0.84);
  cursor: pointer;
  transition: all 0.2s ease;
}

.pro-menu__item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.pro-shell--student .pro-menu__item {
  color: #465064;
}

.pro-shell--student .pro-menu__item:hover {
  background: #dff3ff;
  color: #1d2433;
}

.pro-menu__item.active {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.18) 0%, rgba(96, 165, 250, 0.22) 100%);
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(191, 219, 254, 0.26);
}

.pro-shell--student .pro-menu__item.active {
  background: #c8f7bb;
  color: #1d2433;
  box-shadow: inset 0 0 0 1.5px #1d2433;
}

.pro-menu__item--child {
  width: calc(100% - 28px);
  min-height: 46px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 700;
  text-align: left;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.pro-shell--student .pro-menu__item--child {
  background: #ffffff;
  border: 1.5px solid #1d2433;
  box-shadow: 3px 3px 0 #1d2433;
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
  margin-left: 248px;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.22s ease;
}

.pro-shell--collapsed .pro-main {
  margin-left: 116px;
}

.pro-header {
  position: sticky;
  top: 14px;
  z-index: 1000;
  min-height: 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 14px 14px 0 0;
  padding: 14px 22px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(203, 215, 235, 0.84);
  border-radius: 24px;
  box-shadow: var(--app-shadow);
}

.pro-shell--student .pro-header {
  background: rgba(255, 253, 249, 0.92);
  border: 2px solid #1d2433;
  box-shadow: 8px 8px 0 #1d2433;
}

.pro-shell--teacher .pro-header {
  border-color: rgba(147, 197, 253, 0.9);
}

.pro-shell--admin .pro-header {
  border-color: rgba(196, 181, 253, 0.9);
  background: rgba(255, 255, 255, 0.88);
}

.pro-header__left,
.pro-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pro-header__title {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.pro-header__title span {
  font-size: 11px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-eyebrow);
}

.pro-shell--student .pro-header__title span,
.pro-shell--student .pro-header__title strong {
  font-family: "Fredoka", "Nunito", sans-serif;
}

.pro-header__title strong {
  font-size: 22px;
  line-height: 1.2;
  color: #1f2d3d;
}

.pro-header__badge {
  width: 48px;
  height: 48px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(191, 219, 254, 0.95);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14) 0%, rgba(56, 189, 248, 0.16) 100%);
  color: var(--app-primary-deep);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.pro-shell--student .pro-header__badge {
  border: 1.5px solid #1d2433;
  background: #dff3ff;
  color: #1d2433;
  box-shadow: 3px 3px 0 #1d2433;
}

.pro-shell--admin .pro-header__badge {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.14) 0%, rgba(167, 139, 250, 0.16) 100%);
  color: #6d28d9;
}

.pro-icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  border: 1px solid rgba(203, 215, 235, 0.95);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 248, 255, 0.98) 100%);
  color: #526274;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pro-shell--student .pro-icon-btn {
  border: 1.5px solid #1d2433;
  background: #ffffff;
  color: #1d2433;
  box-shadow: 3px 3px 0 #1d2433;
}

.pro-shell--student .pro-icon-btn:hover {
  background: #dff3ff;
  color: #1d2433;
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
  border: 1px solid rgba(203, 215, 235, 0.95);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 248, 255, 0.98) 100%);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #4f6278;
}

.pro-shell--student .pro-role-chip {
  border: 1.5px solid #1d2433;
  background: #ffffff;
  color: #1d2433;
  box-shadow: 3px 3px 0 #1d2433;
}

.pro-shell--admin .pro-role-chip__dot {
  background: linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%);
  box-shadow: 0 0 0 5px rgba(124, 58, 237, 0.12);
}

.pro-role-chip__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb 0%, #22c55e 100%);
  box-shadow: 0 0 0 5px rgba(37, 99, 235, 0.12);
}

.pro-content {
  flex: 1;
  min-height: 0;
  padding: 24px 14px 24px 0;
  overflow: auto;
  background: radial-gradient(circle at top right, rgba(111, 193, 255, 0.08), transparent 24%), transparent;
}

.pro-shell--student .pro-content {
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.42), transparent 26%),
    transparent;
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
    inset: 12px auto 12px 12px;
    width: 88px;
  }

  .pro-main {
    margin-left: 116px;
  }

  .pro-brand__text,
  .pro-menu__children,
  .pro-menu__section-text {
    display: none;
  }
}

@media (max-width: 760px) {
  .student-shell {
    padding: 12px 12px 24px;
  }

  .student-shell__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .student-shell__nav,
  .student-shell__actions {
    width: 100%;
  }

  .pro-sider {
    inset: 12px auto 12px 12px;
  }

  .pro-header {
    height: auto;
    min-height: 72px;
    margin: 12px 12px 0 0;
    padding: 14px 16px;
    align-items: flex-start;
    flex-direction: column;
  }

  .pro-content {
    padding: 16px 12px 16px 0;
  }
}
</style>
