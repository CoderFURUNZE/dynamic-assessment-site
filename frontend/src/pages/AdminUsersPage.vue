<template>
  <div class="edu-page">
    <header class="edu-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">用户管理</h1>
        <p class="edu-header__desc">统一管理平台用户账号、角色及基础信息。</p>
      </div>
    </header>

    <section class="edu-panel">
      <AdminUserManager mode="users" />
    </section>
  </div>
</template>

<script setup lang="ts">
import AdminUserManager from "../components/AdminUserManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
</script>

<style scoped>.admin-page { display:grid; gap:20px; }</style>
