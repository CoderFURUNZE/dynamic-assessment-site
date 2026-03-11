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
const StudentGraphWorkspacePage = () => import("./pages/StudentGraphWorkspace.vue");
const AdminPage = () => import("./pages/Admin.vue");
const TeacherPage = () => import("./pages/Teacher.vue");
const TeacherGraphWorkspacePage = () => import("./pages/TeacherGraphWorkspace.vue");
const StartPage = () => import("./pages/Start.vue");
const LoginPage = () => import("./pages/Login.vue");
const AdminPreviewPage = () => import("./pages/AdminPreview.vue");

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
  "/student/resource",
  "/student/quiz",
  "/student/practice",
  "/student/report",
].forEach((path) => {
  router.addRoute({ path, component: path === "/student/graph-workspace" ? StudentGraphWorkspacePage : StudentPage });
});

[
  "/admin/config",
  "/admin/persona",
  "/admin/dimensions",
  "/admin/analytics",
  "/admin/video",
  "/admin/questions",
  "/admin/courses",
  "/admin/kps",
  "/admin/edges",
  "/admin/users",
  "/admin/report",
  "/admin/audit",
  "/admin/extensions",
].forEach((path) => {
  router.addRoute({ path, component: AdminPage });
});

[
  "/teacher/courses",
  "/teacher/stages",
  "/teacher/imports",
  "/teacher/indicators",
  "/teacher/graph",
  "/teacher/graph-workspace",
  "/teacher/kps",
  "/teacher/edges",
  "/teacher/video",
  "/teacher/questions",
  "/teacher/analytics",
  "/teacher/profiles",
  "/teacher/students",
  "/teacher/report",
  "/teacher/extensions",
].forEach((path) => {
  router.addRoute({ path, component: path === "/teacher/graph-workspace" ? TeacherGraphWorkspacePage : TeacherPage });
});

router.addRoute({ path: "/student", redirect: "/student/overview" });
router.addRoute({ path: "/student/interview", redirect: "/student/overview" });
router.addRoute({ path: "/student/:pathMatch(.*)*", redirect: "/student/overview" });

router.addRoute({ path: "/admin", redirect: "/admin/config" });
router.addRoute({ path: "/admin/preview", component: AdminPreviewPage });
router.addRoute({ path: "/admin/:pathMatch(.*)*", redirect: "/admin/config" });

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
    return true;
  }
  if (to.path.startsWith("/teacher")) {
    if (role === "student") return "/student/overview";
    if (role === "admin") return "/admin/config";
    return true;
  }
  if (to.path.startsWith("/student")) {
    if (role === "admin") return "/admin/config";
    if (role === "teacher") return "/teacher/courses";
  }
  const username = getUsername();
  if (username) {
    localStorage.setItem(`da_last_route_${username}`, to.fullPath);
  }
  return true;
});
