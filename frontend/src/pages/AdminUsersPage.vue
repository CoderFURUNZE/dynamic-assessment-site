<template>
  <div class="admin-page">
    <PageSectionCard eyebrow="Users" title="用户管理" description="这里单独维护平台用户账号、角色和基础信息。">
      <AdminUserManager mode="users" />
    </PageSectionCard>
  </div>
</template>

<script setup lang="ts">
import AdminUserManager from "../components/AdminUserManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<style scoped>.admin-page { display:grid; gap:20px; }</style>
