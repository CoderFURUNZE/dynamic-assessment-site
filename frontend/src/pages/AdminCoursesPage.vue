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
  gap: 18px;
  min-width: 0;
}

.admin-courses-page__panel {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.22), transparent 28%),
    radial-gradient(circle at bottom left, rgba(187, 247, 208, 0.16), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
  padding: 20px;
  min-width: 0;
  overflow-x: hidden;
}
</style>
