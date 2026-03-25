<script setup lang="ts">
import AdminCourseManager from "../components/AdminCourseManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<template>
  <div class="admin-page">
    <PageSectionCard
      eyebrow="Courses"
      title="课程管理"
      description="管理员在这里统一创建课程、设置报名规则和课程启用状态。"
    >
      <AdminCourseManager />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.admin-page {
  display: grid;
  gap: 20px;
}
</style>
