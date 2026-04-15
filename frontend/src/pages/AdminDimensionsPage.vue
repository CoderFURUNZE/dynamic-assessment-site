<script setup lang="ts">
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminDimensionManager from "../components/AdminDimensionManager.vue";
</script>

<template>
  <div class="admin-dimensions-page">
    <AdminIntroHero eyebrow="评价配置" title="维度指标" pill="指标池" description="统一维护一级维度和二级指标，为动态评价和画像分析提供稳定的指标口径。" />

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
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}
</style>
