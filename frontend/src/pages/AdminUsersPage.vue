<template>
  <div class="edu-page admin-shell-page">
    <header class="edu-header admin-shell-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">用户管理</h1>
        <p class="edu-header__desc">统一管理平台用户账号、角色及基础信息。</p>
      </div>
      <div class="edu-header__actions admin-shell-actions">
        <el-button-group>
          <el-button @click="router.push('/admin/dashboard')">概览</el-button>
          <el-button @click="router.push('/admin/basic/courses')">课程</el-button>
          <el-button type="primary" @click="router.push('/admin/basic/users')">用户</el-button>
          <el-button @click="router.push('/admin/basic/teachers')">老师</el-button>
          <el-button @click="router.push('/admin/evaluation/dimensions')">指标池</el-button>
          <el-button @click="router.push('/admin/evaluation/persona')">画像规则</el-button>
        </el-button-group>
      </div>
    </header>

    <section class="edu-panel admin-shell-panel">
      <AdminUserManager mode="users" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import AdminUserManager from "../components/AdminUserManager.vue";

const router = useRouter();
</script>

<style scoped></style>
