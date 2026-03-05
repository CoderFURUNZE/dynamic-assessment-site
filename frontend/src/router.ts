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
const AdminPage = () => import("./pages/Admin.vue");
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
  "/student/resource",
  "/student/quiz",
  "/student/practice",
  "/student/notes",
].forEach((path) => {
  router.addRoute({ path, component: StudentPage });
});

[
  "/admin/config",
  "/admin/video",
  "/admin/questions",
  "/admin/courses",
  "/admin/kps",
  "/admin/edges",
  "/admin/users",
  "/admin/report",
  "/admin/expression",
  "/admin/audit",
].forEach((path) => {
  router.addRoute({ path, component: AdminPage });
});

router.addRoute({ path: "/student", redirect: "/student/resource" });
router.addRoute({ path: "/student/interview", redirect: "/student/resource" });
router.addRoute({ path: "/student/:pathMatch(.*)*", redirect: "/student/resource" });

router.addRoute({ path: "/admin", redirect: "/admin/config" });
router.addRoute({ path: "/admin/preview", component: AdminPreviewPage });
router.addRoute({ path: "/admin/:pathMatch(.*)*", redirect: "/admin/config" });

router.addRoute({ path: "/:pathMatch(.*)*", redirect: "/start" });

router.beforeEach((to) => {
  if (to.path === "/login" || to.path === "/start") return true;
  if (!getToken()) return "/login";
  const role = getRole();
  if (to.path.startsWith("/admin")) {
    if (role === "student") return "/student/resource";
    return true;
  }
  if (to.path.startsWith("/student")) {
    if (role === "admin" || role === "teacher") return "/admin/config";
  }
  const username = getUsername();
  if (username) {
    localStorage.setItem(`da_last_route_${username}`, to.fullPath);
  }
  return true;
});
