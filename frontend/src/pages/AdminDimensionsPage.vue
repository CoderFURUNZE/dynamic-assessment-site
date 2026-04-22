<script setup lang="ts">
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminDimensionManager from "../components/AdminDimensionManager.vue";
</script>

<template>
  <div class="admin-dimensions-page">
    <AdminIntroHero
      eyebrow="评价配置"
      title="维度与指标"
      pill="指标口径"
      description="统一维护一级维度和二级指标，为动态评价和画像分析提供稳定、可追踪的指标基础。"
    />

    <section class="admin-dimensions-page__panel">
      <AdminDimensionManager />
    </section>
  </div>
</template>

<style scoped>
.admin-dimensions-page {
  display: grid;
  gap: 20px;
}

.admin-dimensions-page__panel {
  padding: 20px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.22), transparent 24%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.16), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}
</style>
