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
  padding: 24px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid #e3ebf5;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}
</style>
