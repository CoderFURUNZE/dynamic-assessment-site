<script setup lang="ts">
import AdminPlatformDashboard from "../components/AdminPlatformDashboard.vue";
</script>

<template>
  <div class="admin-dashboard-page">
    <section class="admin-dashboard-page__hero">
      <div>
        <p class="admin-dashboard-page__eyebrow">平台概览</p>
        <h1 class="admin-dashboard-page__title">后台总览</h1>
        <p class="admin-dashboard-page__desc">首页只保留关键指标和平台状态，课程、用户、评价配置通过左侧导航进入各自页面处理。</p>
      </div>
    </section>

    <section class="admin-dashboard-page__panel">
      <AdminPlatformDashboard />
    </section>
  </div>
</template>

<style scoped>
.admin-dashboard-page {
  display: grid;
  gap: 20px;
}

.admin-dashboard-page__hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  border-radius: 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f4f8ff 100%);
  border: 1px solid #e3ebf5;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.05);
}

.admin-dashboard-page__eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #6b7d91;
  text-transform: uppercase;
}

.admin-dashboard-page__title {
  margin: 0;
  font-size: 28px;
  color: #1f2d3d;
}

.admin-dashboard-page__desc {
  margin: 10px 0 0;
  max-width: 720px;
  color: #62748a;
  line-height: 1.7;
}

.admin-dashboard-page__panel {
  padding: 24px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid #e3ebf5;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}
</style>
