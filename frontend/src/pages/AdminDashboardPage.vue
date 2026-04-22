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
  border-radius: 22px;
  background:
    radial-gradient(circle at top left, rgba(219, 234, 254, 0.22), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}
</style>
