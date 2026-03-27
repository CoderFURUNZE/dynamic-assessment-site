<script setup lang="ts">
import AdminCourseManager from "../components/AdminCourseManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<template>
  <div class="edu-page">
    <header class="edu-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">课程管理</h1>
        <p class="edu-header__desc">在这里统一创建课程、设置报名规则和维护课程启用状态。</p>
      </div>
    </header>

    <section class="edu-panel">
      <AdminCourseManager />
    </section>
  </div>
</template>

<style scoped>
.admin-page {
  display: grid;
  gap: 20px;
}
</style>
