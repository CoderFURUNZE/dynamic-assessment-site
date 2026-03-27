<script setup lang="ts">
import { useRouter } from "vue-router";
import AdminPlatformDashboard from "../components/AdminPlatformDashboard.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import SimpleStepsBar from "../components/SimpleStepsBar.vue";

const router = useRouter();
</script>

<template>
  <div class="edu-page one-screen">
    <header class="edu-header compact">
      <div class="edu-header__left">
        <h1 class="edu-header__title">管理后台</h1>
        <p class="edu-header__desc">概览系统整体运行情况，高效管理用户、老师与画像规则。</p>
      </div>
      <div class="edu-header__actions">
        <el-button-group>
          <el-button @click="router.push('/admin/courses')">课程管理</el-button>
          <el-button @click="router.push('/admin/users')">用户管理</el-button>
          <el-button @click="router.push('/admin/teachers')">老师管理</el-button>
          <el-button type="primary" @click="router.push('/admin/persona')">画像规则</el-button>
        </el-button-group>
      </div>
    </header>

    <section class="edu-panel main-layout-content">
      <header class="edu-panel__header">
        <h2 class="edu-panel__title">平台运行概览</h2>
      </header>
      <div class="scroll-area-internal">
        <AdminPlatformDashboard />
      </div>
    </section>
  </div>
</template>

<style scoped>
.one-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.edu-header.compact {
  margin-bottom: 16px;
  padding: 12px 0;
}

.main-layout-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 24px;
}

.scroll-area-internal {
  flex: 1;
  overflow-y: auto;
}

@media (max-height: 800px) {
  .edu-header__desc { display: none; }
}
</style>
