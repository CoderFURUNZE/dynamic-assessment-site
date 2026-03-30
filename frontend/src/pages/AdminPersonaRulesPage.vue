<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";

const personaSubject = ref("计算机网络");
const personaGrade = ref("通用");
const router = useRouter();
</script>

<template>
  <div class="edu-page admin-shell-page">
    <header class="edu-header admin-shell-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">画像规则管理</h1>
        <p class="edu-header__desc">按课程上下文维护画像阈值、权重和策略，确保评估规则统一。</p>
      </div>
      <div class="edu-header__actions admin-shell-actions">
        <el-button-group>
          <el-button @click="router.push('/admin')">概览</el-button>
          <el-button @click="router.push('/admin/courses')">课程</el-button>
          <el-button @click="router.push('/admin/users')">用户</el-button>
          <el-button @click="router.push('/admin/teachers')">老师</el-button>
          <el-button @click="router.push('/admin/dimensions')">指标池</el-button>
          <el-button type="primary" @click="router.push('/admin/persona')">画像规则</el-button>
        </el-button-group>
      </div>
    </header>

    <section class="edu-panel admin-shell-panel">
      <el-card class="panel-card" shadow="never">
        <template #header>规则上下文</template>
        <div class="admin-context">
          <el-input v-model="personaSubject" placeholder="学科（如：计算机网络）" />
          <el-input v-model="personaGrade" placeholder="层级（如：通用）" />
        </div>
      </el-card>
      <AdminPersonaManager :subject="personaSubject" :grade="personaGrade" />
    </section>
  </div>
</template>

<style scoped>
.admin-shell-panel {
  display: grid;
  gap: 16px;
}
.admin-context { display:grid; gap:12px; grid-template-columns:1fr 1fr; }
@media (max-width: 900px) { .admin-context { grid-template-columns:1fr; } }
</style>
