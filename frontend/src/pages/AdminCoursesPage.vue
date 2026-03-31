<script setup lang="ts">
import AdminCourseManager from "../components/AdminCourseManager.vue";
</script>

<template>
  <div class="admin-courses-page">
    <section class="admin-courses-page__hero">
      <div>
        <span class="admin-courses-page__eyebrow">课程管理</span>
        <h1>统一维护课程基础信息和报名配置</h1>
        <p>课程创建、教师绑定、报名规则和状态切换都放在这个页面处理，不再重复放一套顶部跳转按钮。</p>
      </div>
    </section>

    <section class="admin-courses-page__panel">
      <AdminCourseManager />
    </section>
  </div>
</template>

<style scoped>
.admin-courses-page { display: grid; gap: 20px; }
.admin-courses-page__hero,
.admin-courses-page__panel {
  border-radius: 24px;
  border: 1px solid #e3ebf5;
  background: #fff;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}
.admin-courses-page__hero {
  padding: 24px 28px;
  background: linear-gradient(135deg, #ffffff 0%, #f4f8ff 100%);
}
.admin-courses-page__eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #6b7d91;
  text-transform: uppercase;
}
.admin-courses-page__hero h1 { margin: 8px 0 0; font-size: 28px; color: #1f2d3d; }
.admin-courses-page__hero p { margin: 10px 0 0; max-width: 720px; color: #62748a; line-height: 1.7; }
.admin-courses-page__panel { padding: 24px; }
</style>
