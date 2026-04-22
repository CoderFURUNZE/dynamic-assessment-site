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
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.22), transparent 24%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.16), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
  min-width: 0;
  overflow-x: hidden;
}
</style>
