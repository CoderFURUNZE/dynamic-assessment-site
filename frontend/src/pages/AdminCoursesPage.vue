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
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.32), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  padding: 24px;
  min-width: 0;
  overflow-x: hidden;
}
</style>
