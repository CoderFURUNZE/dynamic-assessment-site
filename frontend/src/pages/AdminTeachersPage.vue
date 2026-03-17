<template>
  <div class="admin-page">
    <PageSectionCard eyebrow="Teachers" title="老师管理" description="把教师账号和负责范围放到独立页面维护，减少和其它后台操作的干扰。">
      <AdminUserManager mode="teachers" />
    </PageSectionCard>
  </div>
</template>

<script setup lang="ts">
import AdminUserManager from "../components/AdminUserManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<style scoped>.admin-page { display:grid; gap:20px; }</style>
