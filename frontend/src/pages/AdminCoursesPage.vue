<script setup lang="ts">
import { useRouter } from "vue-router";
import AdminCourseManager from "../components/AdminCourseManager.vue";

const router = useRouter();
</script>

<template>
  <div class="edu-page admin-shell-page">
    <header class="edu-header admin-shell-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">课程管理</h1>
        <p class="edu-header__desc">在这里统一创建课程、设置报名规则和维护课程启用状态。</p>
      </div>
      <div class="edu-header__actions admin-shell-actions">
        <el-button-group>
          <el-button @click="router.push('/admin')">概览</el-button>
          <el-button type="primary" @click="router.push('/admin/courses')">课程</el-button>
          <el-button @click="router.push('/admin/users')">用户</el-button>
          <el-button @click="router.push('/admin/teachers')">老师</el-button>
          <el-button @click="router.push('/admin/dimensions')">指标池</el-button>
          <el-button @click="router.push('/admin/persona')">画像规则</el-button>
        </el-button-group>
      </div>
    </header>

    <section class="edu-panel admin-shell-panel">
      <AdminCourseManager />
    </section>
  </div>
</template>

<style scoped></style>
