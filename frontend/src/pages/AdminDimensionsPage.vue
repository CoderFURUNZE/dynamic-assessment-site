<template>
  <div class="admin-page">
    <PageSectionCard eyebrow="Dimensions" title="指标池管理" description="指标池和子指标集中在一页维护，避免和老师、规则页面来回切换。">
      <AdminDimensionManager />
    </PageSectionCard>
  </div>
</template>

<script setup lang="ts">
import AdminDimensionManager from "../components/AdminDimensionManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<style scoped>.admin-page { display:grid; gap:20px; }</style>
