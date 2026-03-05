<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearToken, getRole, getToken } from "./token";
import { isLoading } from "./loading";

const route = useRoute();
const router = useRouter();

const role = computed(() => getRole() || "");
const isAdmin = computed(() => role.value === "admin" || role.value === "teacher");

const routeGroup = computed<"admin" | "student" | "start" | "login">(() => {
  if (route.path.startsWith("/admin")) return "admin";
  if (route.path.startsWith("/student")) return "student";
  if (route.path === "/start") return "start";
  return "login";
});

const isAuthPage = computed(() => routeGroup.value === "login" || routeGroup.value === "start");

function logout() {
  clearToken();
  router.push("/login");
}
</script>

<template>
  <el-container class="app-shell" :class="{ 'login-container': isAuthPage }">
    <el-header v-if="!isAuthPage" class="app-header">
      <div class="app-brand">动态评价系统</div>
      <div class="app-menu-label">{{ routeGroup === "admin" ? "管理端" : "学习者端" }}</div>
      <div style="display: flex; align-items: center; gap: 10px">
        <el-button v-if="routeGroup === 'admin' && isAdmin" size="small" @click="router.push('/admin/preview')">
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
  background: rgba(0, 0, 0, 0.25);
  color: #fff;
  z-index: 3000;
  font-size: 15px;
  backdrop-filter: blur(2px);
}
</style>
