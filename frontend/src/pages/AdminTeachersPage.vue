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
  padding: 18px;
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  min-width: 0;
  overflow-x: hidden;
}
</style>
