import { createRouter, createWebHistory } from "vue-router";
import { getRole, getToken, getUsername } from "./token";

export const router = createRouter({
  history: createWebHistory(),
  routes: [],
});

function persistLastRoute(fullPath: string) {
  const username = getUsername();
  if (!username) return;
  if (fullPath.startsWith("/student/graph-fullscreen") || fullPath.startsWith("/teacher/graph-fullscreen")) return;
  localStorage.setItem(`da_last_route_${username}`, fullPath);
}

const StudentDashboardPage = () => import("./pages/StudentDashboardPage.vue");
const StudentQuestionnairePage = () => import("./pages/StudentQuestionnairePage.vue");
const StudentReportPage = () => import("./pages/StudentReportPage.vue");
const StudentGraphWorkspacePage = () => import("./pages/StudentGraphWorkspace.vue");
const StudentGraphFullscreenPage = () => import("./pages/StudentGraphFullscreenPage.vue");
const StudentKpContentWorkspacePage = () => import("./pages/StudentKpContentWorkspace.vue");
const StudentEnrollPage = () => import("./pages/StudentEnroll.vue");

const AdminDashboardPage = () => import("./pages/AdminDashboardPage.vue");
const AdminCoursesPage = () => import("./pages/AdminCoursesPage.vue");
const AdminUsersPage = () => import("./pages/AdminUsersPage.vue");
const AdminTeachersPage = () => import("./pages/AdminTeachersPage.vue");
const AdminDimensionsPage = () => import("./pages/AdminDimensionsPage.vue");
const AdminPersonaStepPage = () => import("./pages/AdminPersonaStepPage.vue");
const AdminAuditPage = () => import("./pages/AdminAuditPage.vue");

const TeacherWorkspacePage = () => import("./pages/TeacherCoursesPage.vue");
const TeacherGraphWorkspacePage = () => import("./pages/TeacherGraphWorkspace.vue");
const TeacherGraphFullscreenPage = () => import("./pages/TeacherGraphFullscreenPage.vue");
const TeacherEvaluationWorkspacePage = () => import("./pages/TeacherEvaluationWorkspacePage.vue");
const TeacherStudentsWorkspacePage = () => import("./pages/TeacherStudentsWorkspacePage.vue");
const TeacherReviewWorkspacePage = () => import("./pages/TeacherReviewWorkspacePage.vue");
const TeacherKpContentWorkspacePage = () => import("./pages/TeacherKpContentWorkspace.vue");
const TeacherResourceDetailPage = () => import("./pages/TeacherResourceDetail.vue");
const TeacherKpPreviewPage = () => import("./pages/StudentKpContentWorkspace.vue");

const StartPage = () => import("./pages/Start.vue");
const LoginPage = () => import("./pages/Login.vue");

router.addRoute({
  path: "/",
  redirect: "/start",
});

router.addRoute({
  path: "/start",
  component: StartPage,
  meta: { title: "开始使用" },
});

router.addRoute({
  path: "/login",
  redirect: "/login/student",
});
router.addRoute({
  path: "/login/student",
  component: LoginPage,
  meta: { title: "学生登录" },
});
router.addRoute({
  path: "/login/staff",
  component: LoginPage,
  meta: { title: "教师与管理员登录" },
});

router.addRoute({
  path: "/student",
  redirect: (to) => ({ path: "/student/dashboard", query: to.query }),
});
router.addRoute({
  path: "/student/dashboard",
  component: StudentDashboardPage,
  meta: { title: "学习总览" },
});
router.addRoute({
  path: "/student/overview",
  redirect: (to) => ({ path: "/student/dashboard", query: to.query }),
});
router.addRoute({
  path: "/student/graph",
  redirect: (to) => ({ path: "/student/graph-workspace", query: to.query }),
});
router.addRoute({
  path: "/student/graph-workspace",
  component: StudentGraphWorkspacePage,
  meta: { title: "知识图谱" },
});
router.addRoute({
  path: "/student/graph-fullscreen",
  component: StudentGraphFullscreenPage,
  meta: { title: "全屏学习图谱", standaloneWorkspace: true },
});
router.addRoute({
  path: "/student/enroll",
  component: StudentEnrollPage,
  meta: { title: "课程加入" },
});
router.addRoute({
  path: "/student/questionnaire",
  component: StudentQuestionnairePage,
  meta: { title: "补充问卷" },
});
router.addRoute({
  path: "/student/report",
  component: StudentReportPage,
  meta: { title: "学习报告" },
});
router.addRoute({
  path: "/admin/config",
  redirect: (to) => ({ path: "/admin/evaluation/persona/settings", query: to.query }),
});
router.addRoute({
  path: "/admin/audit",
  component: AdminAuditPage,
  meta: { title: "审计日志" },
});
[
  "/student/kp-content/:kpId",
  "/student/kp-content/:kpId/practice",
  "/student/kp-content/:kpId/records",
  "/student/kp-content/:kpId/wrong",
  "/student/kp-content/:kpId/review",
].forEach((path) => {
  router.addRoute({
    path,
    component: StudentKpContentWorkspacePage,
    meta: { title: "知识点学习" },
  });
});
[
  "/student/resource",
  "/student/quiz",
  "/student/practice",
].forEach((path) => {
  router.addRoute({
    path,
    redirect: (to) => ({ path: "/student/dashboard", query: to.query }),
  });
});

router.addRoute({ path: "/admin", redirect: "/admin/dashboard" });
router.addRoute({
  path: "/admin/dashboard",
  component: AdminDashboardPage,
  meta: { title: "平台概览" },
});
router.addRoute({
  path: "/admin/basic/courses",
  component: AdminCoursesPage,
  meta: { title: "课程管理" },
});
router.addRoute({
  path: "/admin/basic/users",
  component: AdminUsersPage,
  meta: { title: "用户管理" },
});
router.addRoute({
  path: "/admin/basic/teachers",
  component: AdminTeachersPage,
  meta: { title: "教师管理" },
});
router.addRoute({
  path: "/admin/evaluation/dimensions",
  component: AdminDimensionsPage,
  meta: { title: "维度与指标" },
});
router.addRoute({
  path: "/admin/evaluation/persona",
  redirect: (to) => ({ path: "/admin/evaluation/persona/settings", query: to.query }),
});
router.addRoute({
  path: "/admin/evaluation/persona/settings",
  component: AdminPersonaStepPage,
  props: { mode: "settings" },
  meta: { title: "基础规则设置" },
});
router.addRoute({
  path: "/admin/evaluation/persona/results",
  redirect: (to) => ({ path: "/admin/evaluation/persona/settings", query: to.query }),
});
[
  "/admin/evaluation/persona/context",
  "/admin/evaluation/persona/thresholds",
  "/admin/evaluation/persona/rules",
].forEach((path) => {
  router.addRoute({
    path,
    redirect: (to) => ({ path: "/admin/evaluation/persona/settings", query: to.query }),
  });
});
[
  ["/admin/courses", "/admin/basic/courses"],
  ["/admin/users", "/admin/basic/users"],
  ["/admin/teachers", "/admin/basic/teachers"],
  ["/admin/dimensions", "/admin/evaluation/dimensions"],
  ["/admin/persona", "/admin/evaluation/persona"],
].forEach(([from, to]) => {
  router.addRoute({ path: from, redirect: to });
});
router.addRoute({ path: "/admin/:pathMatch(.*)*", redirect: "/admin/dashboard" });

router.addRoute({
  path: "/teacher",
  redirect: (to) => ({ path: "/teacher/workspace", query: to.query }),
});
router.addRoute({
  path: "/teacher/workspace",
  component: TeacherWorkspacePage,
  meta: { title: "课程工作台" },
});
router.addRoute({
  path: "/teacher/content",
  component: TeacherGraphWorkspacePage,
  meta: { title: "内容建设" },
});
router.addRoute({
  path: "/teacher/graph-fullscreen",
  component: TeacherGraphFullscreenPage,
  meta: { title: "全屏编辑图谱", standaloneWorkspace: true },
});
router.addRoute({
  path: "/teacher/evaluation",
  component: TeacherEvaluationWorkspacePage,
  meta: { title: "阶段评价" },
});
router.addRoute({
  path: "/teacher/students",
  component: TeacherStudentsWorkspacePage,
  meta: { title: "学生分析" },
});
router.addRoute({
  path: "/teacher/review",
  component: TeacherReviewWorkspacePage,
  meta: { title: "审核与评定" },
});
router.addRoute({
  path: "/teacher/resources/:resourceId",
  component: TeacherResourceDetailPage,
  meta: { title: "资源详情" },
});
router.addRoute({
  path: "/teacher/kp-content/:kpId",
  component: TeacherKpContentWorkspacePage,
  meta: { title: "知识点配置工作台" },
});
[
  "/teacher/kp-preview/:kpId",
  "/teacher/kp-preview/:kpId/practice",
  "/teacher/kp-preview/:kpId/records",
  "/teacher/kp-preview/:kpId/wrong",
  "/teacher/kp-preview/:kpId/review",
].forEach((path) => {
  router.addRoute({
    path,
    component: TeacherKpPreviewPage,
    meta: { title: "学生端预览" },
  });
});
[
  ["/teacher/courses", "/teacher/workspace"],
  ["/teacher/graph", "/teacher/content"],
  ["/teacher/graph-workspace", "/teacher/content"],
  ["/teacher/stages", "/teacher/evaluation?tab=stages"],
  ["/teacher/imports", "/teacher/evaluation?tab=imports"],
  ["/teacher/indicators", "/teacher/evaluation?tab=indicators"],
  ["/teacher/behavior-report", "/teacher/evaluation?tab=behavior"],
  ["/teacher/analytics", "/teacher/students?tab=class"],
  ["/teacher/profiles", "/teacher/students?tab=results"],
  ["/teacher/enrollments", "/teacher/review?tab=enrollment"],
  ["/teacher/final-review", "/teacher/review?tab=final"],
].forEach(([from, to]) => {
  router.addRoute({
    path: from,
    redirect: (route) => {
      const [path, rawQuery] = to.split("?");
      const nextQuery = { ...route.query } as Record<string, string | string[]>;
      if (rawQuery) {
        rawQuery.split("&").forEach((entry) => {
          const [key, value] = entry.split("=");
          nextQuery[key] = value;
        });
      }
      return { path, query: nextQuery };
    },
  });
});
router.addRoute({
  path: "/teacher/:pathMatch(.*)*",
  redirect: (to) => ({ path: "/teacher/workspace", query: to.query }),
});

router.addRoute({ path: "/:pathMatch(.*)*", redirect: "/start" });

router.beforeEach((to) => {
  if (to.path === "/start" || to.path.startsWith("/login")) return true;
  if (!getToken()) return "/login/student";
  const role = getRole();
  if (to.path === "/student/graph-fullscreen") {
    return true;
  }
  if (to.path === "/teacher/graph-fullscreen" && role === "student") {
    return { path: "/student/graph-fullscreen", query: to.query };
  }
  if (to.path.startsWith("/admin")) {
    if (role === "student") return "/student/dashboard";
    if (role === "teacher") return "/teacher/workspace";
    if (role === "admin") {
      const allowedAdminPaths = new Set([
        "/admin",
        "/admin/dashboard",
        "/admin/audit",
        "/admin/basic/courses",
        "/admin/basic/users",
        "/admin/basic/teachers",
        "/admin/evaluation/dimensions",
        "/admin/evaluation/persona",
        "/admin/evaluation/persona/context",
        "/admin/evaluation/persona/thresholds",
        "/admin/evaluation/persona/rules",
        "/admin/evaluation/persona/settings",
        "/admin/config",
      ]);
      if (!allowedAdminPaths.has(to.path)) return "/admin/dashboard";
    }
    persistLastRoute(to.fullPath);
    return true;
  }
  if (to.path.startsWith("/teacher")) {
    if (role === "student") return "/student/dashboard";
    if (role === "admin") return "/admin/dashboard";
    persistLastRoute(to.fullPath);
    return true;
  }
  if (to.path.startsWith("/student")) {
    const preview = String(to.query.preview || "");
    const previewEnabled = preview === "1";
    if (role === "admin" && !previewEnabled) return "/admin/dashboard";
    if (role === "teacher" && !previewEnabled) return "/teacher/workspace";
  }
  persistLastRoute(to.fullPath);
  return true;
});

router.afterEach((to) => {
  if (typeof document === "undefined") return;
  const pageTitle = String(to.meta?.title || "").trim();
  document.title = pageTitle ? `${pageTitle} | 动态评价系统` : "动态评价系统";
});



