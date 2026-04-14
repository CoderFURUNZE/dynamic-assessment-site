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
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #e3ebf5;
  box-shadow: var(--app-shadow);
}
</style>
