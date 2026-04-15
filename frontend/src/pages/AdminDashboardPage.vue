<script setup lang="ts">
import AdminPlatformDashboard from "../components/AdminPlatformDashboard.vue";
import AdminIntroHero from "../components/AdminIntroHero.vue";
</script>

<template>
  <div class="admin-dashboard-page">
    <AdminIntroHero
      eyebrow="平台概览"
      title="后台总览"
      pill="关键指标"
    />

    <section class="admin-dashboard-page__panel">
      <AdminPlatformDashboard />
    </section>
  </div>
</template>

<style scoped>
.admin-dashboard-page {
  display: grid;
  gap: 20px;
}

.admin-dashboard-page__panel {
  padding: 26px;
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  border: 3px solid #1f2937;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}
</style>
