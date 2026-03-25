<script setup lang="ts">
import { useRouter } from "vue-router";
import AdminPlatformDashboard from "../components/AdminPlatformDashboard.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import SimpleStepsBar from "../components/SimpleStepsBar.vue";

const router = useRouter();
</script>

<template>
  <div class="admin-page">
    <SimpleStepsBar :items="['先看平台概览', '再管用户', '再管老师', '最后维护规则']" />

    <PageSectionCard eyebrow="Platform" title="平台概览" description="先看整体运行情况，再进入用户、老师和规则等独立管理页面。">
      <template #actions>
          <el-button @click="router.push('/admin/courses')">课程管理</el-button>
          <el-button @click="router.push('/admin/users')">用户管理</el-button>
          <el-button @click="router.push('/admin/teachers')">老师管理</el-button>
          <el-button type="primary" @click="router.push('/admin/persona')">画像规则</el-button>
      </template>
      <AdminPlatformDashboard />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.admin-page { display:grid; gap:20px; }
</style>
