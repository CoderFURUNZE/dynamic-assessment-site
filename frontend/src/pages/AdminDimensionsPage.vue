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
  border-radius: 24px;
  border: 1px solid #e3ebf5;
  background: #fff;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}
</style>
