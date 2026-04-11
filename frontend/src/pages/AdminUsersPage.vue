<script setup lang="ts">
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminUserManager from "../components/AdminUserManager.vue";
</script>

<template>
  <div class="admin-users-page">
    <AdminIntroHero eyebrow="基础管理" title="用户管理" pill="账号维护" />

    <section class="admin-users-page__panel">
      <AdminUserManager mode="users" />
    </section>
  </div>
</template>

<style scoped>
.admin-users-page {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.admin-users-page__panel {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  min-width: 0;
  overflow-x: hidden;
}
</style>
