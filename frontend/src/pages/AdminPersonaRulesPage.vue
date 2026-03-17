<script setup lang="ts">
import { ref } from "vue";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";
import PageSectionCard from "../components/PageSectionCard.vue";

const personaSubject = ref("计算机网络");
const personaGrade = ref("通用");
</script>

<template>
  <div class="admin-page">
    <PageSectionCard eyebrow="Persona Rules" title="画像规则管理" description="先确定规则上下文，再单独维护画像规则，避免后台页面信息过载。">
      <el-card class="panel-card" shadow="never">
        <template #header>规则上下文</template>
        <div class="admin-context">
          <el-input v-model="personaSubject" placeholder="学科（如：计算机网络）" />
          <el-input v-model="personaGrade" placeholder="层级（如：通用）" />
        </div>
      </el-card>
      <AdminPersonaManager :subject="personaSubject" :grade="personaGrade" />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.admin-page { display:grid; gap:20px; }
.admin-context { display:grid; gap:12px; grid-template-columns:1fr 1fr; }
@media (max-width: 900px) { .admin-context { grid-template-columns:1fr; } }
</style>
