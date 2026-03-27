<template>
  <div class="edu-page">
    <header class="edu-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">老师管理</h1>
        <p class="edu-header__desc">维护教师账号及权限，支持批量管理与状态切换。</p>
      </div>
    </header>

    <section class="edu-panel">
      <AdminUserManager mode="teachers" />
    </section>
  </div>
</template>

<script setup lang="ts">
import AdminUserManager from "../components/AdminUserManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<style scoped>.admin-page { display:grid; gap:20px; }</style>
