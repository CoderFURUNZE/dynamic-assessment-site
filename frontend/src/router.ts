import { createRouter, createWebHistory } from "vue-router";
import { getRole, getToken, getUsername } from "./token";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 复用同一个异步组件引用，避免同页签切换时重复创建包装组件导致偶发空白
    // eslint-disable-next-line @typescript-eslint/no-use-before-define
  ],
});

const StudentPage = () => import("./pages/Student.vue");
const StudentQuestionnairePage = () => import("./pages/StudentQuestionnairePage.vue");
const StudentReportPage = () => import("./pages/StudentReportPage.vue");
const StudentGraphWorkspacePage = () => import("./pages/StudentGraphWorkspace.vue");
const StudentKpContentWorkspacePage = () => import("./pages/StudentKpContentWorkspace.vue");
const StudentEnrollPage = () => import("./pages/StudentEnroll.vue");
const AdminDashboardPage = () => import("./pages/AdminDashboardPage.vue");
const AdminUsersPage = () => import("./pages/AdminUsersPage.vue");
const AdminTeachersPage = () => import("./pages/AdminTeachersPage.vue");
const AdminDimensionsPage = () => import("./pages/AdminDimensionsPage.vue");
const AdminPersonaRulesPage = () => import("./pages/AdminPersonaRulesPage.vue");
const TeacherCoursesPage = () => import("./pages/TeacherCoursesPage.vue");
const TeacherStagesPage = () => import("./pages/TeacherStagesPage.vue");
const TeacherImportsPage = () => import("./pages/TeacherImportsPage.vue");
const TeacherIndicatorsPage = () => import("./pages/TeacherIndicatorsPage.vue");
const TeacherAnalyticsPage = () => import("./pages/TeacherAnalyticsPage.vue");
const TeacherProfilesPage = () => import("./pages/TeacherProfilesPage.vue");
const TeacherStudentsPage = () => import("./pages/TeacherStudentsPage.vue");
const TeacherGraphWorkspacePage = () => import("./pages/TeacherGraphWorkspace.vue");
const TeacherKpContentWorkspacePage = () => import("./pages/TeacherKpContentWorkspace.vue");
const TeacherResourceDetailPage = () => import("./pages/TeacherResourceDetail.vue");
const TeacherEnrollmentReviewPage = () => import("./pages/TeacherEnrollmentReview.vue");
const TeacherFinalScoreReviewPage = () => import("./pages/TeacherFinalScoreReview.vue");
const StartPage = () => import("./pages/Start.vue");
const LoginPage = () => import("./pages/Login.vue");

router.addRoute({
  path: "/",
  redirect: "/start",
});

router.addRoute({
  path: "/start",
  component: StartPage,
});

router.addRoute({
  path: "/login",
  component: LoginPage,
});

[
  "/student/overview",
  "/student/graph",
  "/student/graph-workspace",
  "/student/enroll",
  "/student/kp-content/:kpId",
  "/student/questionnaire",
  "/student/report",
].forEach((path) => {
  if (path === "/student/graph") {
    router.addRoute({ path, redirect: "/student/graph-workspace" });
    return;
  }
  if (path === "/student/graph-workspace") {
    router.addRoute({ path, component: StudentGraphWorkspacePage });
    return;
  }
  if (path === "/student/enroll") {
    router.addRoute({ path, component: StudentEnrollPage });
    return;
  }
  if (path === "/student/kp-content/:kpId") {
    router.addRoute({ path, component: StudentKpContentWorkspacePage });
    return;
  }
  if (path === "/student/questionnaire") {
    router.addRoute({ path, component: StudentQuestionnairePage });
    return;
  }
  if (path === "/student/report") {
    router.addRoute({ path, component: StudentReportPage });
    return;
  }
  router.addRoute({ path, component: StudentPage });
});

[
  "/admin/dashboard",
  "/admin/users",
  "/admin/teachers",
  "/admin/dimensions",
  "/admin/persona",
].forEach((path) => {
  const component = {
    "/admin/dashboard": AdminDashboardPage,
    "/admin/users": AdminUsersPage,
    "/admin/teachers": AdminTeachersPage,
    "/admin/dimensions": AdminDimensionsPage,
    "/admin/persona": AdminPersonaRulesPage,
  }[path] ?? AdminDashboardPage;
  router.addRoute({ path, component });
});

[
  "/teacher/courses",
  "/teacher/stages",
  "/teacher/imports",
  "/teacher/indicators",
  "/teacher/enrollments",
  "/teacher/final-review",
  "/teacher/graph",
  "/teacher/graph-workspace",
  "/teacher/analytics",
  "/teacher/profiles",
  "/teacher/students",
].forEach((path) => {
  if (path === "/teacher/graph") {
    router.addRoute({ path, redirect: "/teacher/graph-workspace" });
    return;
  }
  const component = {
    "/teacher/courses": TeacherCoursesPage,
    "/teacher/stages": TeacherStagesPage,
    "/teacher/imports": TeacherImportsPage,
    "/teacher/indicators": TeacherIndicatorsPage,
    "/teacher/analytics": TeacherAnalyticsPage,
    "/teacher/profiles": TeacherProfilesPage,
    "/teacher/students": TeacherStudentsPage,
    "/teacher/graph-workspace": TeacherGraphWorkspacePage,
    "/teacher/enrollments": TeacherEnrollmentReviewPage,
    "/teacher/final-review": TeacherFinalScoreReviewPage,
  }[path] ?? TeacherCoursesPage;
  router.addRoute({ path, component });
});
router.addRoute({ path: "/teacher/resources/:resourceId", component: TeacherResourceDetailPage });
router.addRoute({ path: "/teacher/kp-content/:kpId", component: TeacherKpContentWorkspacePage });

router.addRoute({ path: "/student", redirect: "/student/overview" });
router.addRoute({ path: "/student/interview", redirect: "/student/overview" });
router.addRoute({ path: "/student/resource", redirect: "/student/graph" });
router.addRoute({ path: "/student/quiz", redirect: "/student/graph" });
router.addRoute({ path: "/student/practice", redirect: "/student/graph" });
router.addRoute({ path: "/student/:pathMatch(.*)*", redirect: "/student/overview" });

router.addRoute({ path: "/admin", redirect: "/admin/dashboard" });
router.addRoute({ path: "/admin/:pathMatch(.*)*", redirect: "/admin/dashboard" });

router.addRoute({ path: "/teacher", redirect: "/teacher/courses" });
router.addRoute({ path: "/teacher/:pathMatch(.*)*", redirect: "/teacher/courses" });

router.addRoute({ path: "/:pathMatch(.*)*", redirect: "/start" });

router.beforeEach((to) => {
  if (to.path === "/login" || to.path === "/start") return true;
  if (!getToken()) return "/login";
  const role = getRole();
  if (to.path.startsWith("/admin")) {
    if (role === "student") return "/student/overview";
    if (role === "teacher") return "/teacher/courses";
    if (role === "admin") {
      const allowedAdminPaths = new Set([
        "/admin",
        "/admin/dashboard",
        "/admin/users",
        "/admin/teachers",
        "/admin/dimensions",
        "/admin/persona",
      ]);
      if (!allowedAdminPaths.has(to.path)) return "/admin/dashboard";
    }
    return true;
  }
  if (to.path.startsWith("/teacher")) {
    if (role === "student") return "/student/overview";
    if (role === "admin") return "/admin/dashboard";
    return true;
  }
  if (to.path.startsWith("/student")) {
    if (role === "admin") return "/admin/dashboard";
    if (role === "teacher") {
      const preview = String(to.query.preview || "");
      if (preview !== "1") return "/teacher/courses";
    }
  }
  const username = getUsername();
  if (username) {
    localStorage.setItem(`da_last_route_${username}`, to.fullPath);
  }
  return true;
});
