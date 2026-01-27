import { createRouter, createWebHistory } from "vue-router";
import Login from "./pages/Login.vue";
import Student from "./pages/Student.vue";
import Admin from "./pages/Admin.vue";
import AdminPreview from "./pages/AdminPreview.vue";
import { getRole, getToken, getUsername } from "./token";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/student/resource" },
    { path: "/login", component: Login },
    { path: "/student", redirect: "/student/resource" },
    { path: "/student/overview", component: Student },
    { path: "/student/resource", component: Student },
    { path: "/student/quiz", component: Student },
    { path: "/student/practice", component: Student },
    { path: "/student/interview", component: Student },
    { path: "/student/notes", component: Student },
    { path: "/admin", redirect: "/admin/config" },
    { path: "/admin/config", component: Admin },
    { path: "/admin/video", component: Admin },
    { path: "/admin/questions", component: Admin },
    { path: "/admin/kps", component: Admin },
    { path: "/admin/edges", component: Admin },
    { path: "/admin/users", component: Admin },
    { path: "/admin/report", component: Admin },
    { path: "/admin/expression", component: Admin },
    { path: "/admin/preview", component: AdminPreview },
  ],
});

router.beforeEach((to) => {
  if (to.path === "/login") return true;
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
