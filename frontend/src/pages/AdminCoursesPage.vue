<script setup lang="ts">
import AdminCourseManager from "../components/AdminCourseManager.vue";
import AdminIntroHero from "../components/AdminIntroHero.vue";
</script>

<template>
  <div class="admin-courses-page">
    <AdminIntroHero eyebrow="基础管理" title="课程管理" pill="课程配置" />

    <section class="admin-courses-page__panel">
      <AdminCourseManager />
    </section>
  </div>
</template>

<style scoped>
.admin-courses-page {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.admin-courses-page__panel {
  border: none;
  background: transparent;
  box-shadow: none;
  padding: 0;
  min-width: 0;
  overflow-x: hidden;
}
</style>
