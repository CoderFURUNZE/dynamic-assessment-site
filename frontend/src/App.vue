<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearToken, getRole, getToken, getUsername } from "./token";

const route = useRoute();
const router = useRouter();
const role = computed(() => getRole() || "");
const isAdmin = computed(() => role.value === "admin" || role.value === "teacher");
const routeGroup = computed(() => {
  if (route.path.startsWith("/admin")) return "admin";
  if (route.path.startsWith("/student")) return "student";
  return "login";
});
const theme = ref("light");
const themeOptions = [
  { value: "light", label: "清新浅色" },
  { value: "dark", label: "沉静深色" },
  { value: "sage", label: "护眼浅绿" },
  { value: "warm", label: "暖阳柔和" },
];

function logout() {
  clearToken();
  router.push("/login");
}

function themeKey() {
  const username = getUsername() || "guest";
  return `da_theme_${username}`;
}

function applyTheme(value: string) {
  theme.value = value;
  document.documentElement.setAttribute("data-theme", value);
  localStorage.setItem(themeKey(), value);
}

onMounted(() => {
  const saved = localStorage.getItem(themeKey());
  applyTheme(saved || "light");
});
</script>

<template>
  <el-container class="app-shell">
    <el-header v-if="routeGroup !== 'login'" class="app-header">
      <div class="app-brand">动态评价系统</div>
      <div class="app-menu-label">{{ routeGroup === "admin" ? "管理端" : "学习者端" }}</div>
      <div style="display: flex; align-items: center; gap: 10px">
        <el-select v-model="theme" size="small" style="width: 130px" @change="applyTheme">
          <el-option v-for="opt in themeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button
          v-if="routeGroup === 'admin' && isAdmin"
          size="small"
          @click="router.push('/admin/preview')"
        >
          学习者端预览
        </el-button>
        <el-button v-if="getToken()" type="default" @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>
