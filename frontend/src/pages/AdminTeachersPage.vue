<script setup lang="ts">
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminUserManager from "../components/AdminUserManager.vue";
</script>

<template>
  <div class="admin-teachers-page">
    <AdminIntroHero eyebrow="基础管理" title="教师管理" pill="教师账号" />

    <section class="admin-teachers-page__panel">
      <AdminUserManager mode="teachers" />
    </section>
  </div>
</template>

<style scoped>
.admin-teachers-page {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.admin-teachers-page__panel {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  min-width: 0;
  overflow-x: hidden;
}
</style>
