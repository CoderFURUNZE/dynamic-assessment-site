<script setup lang="ts">
import { ref } from "vue";
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";

const personaSubject = ref("计算机网络");
const personaGrade = ref("通用");
</script>

<template>
  <div class="admin-persona-page">
    <AdminIntroHero eyebrow="评价配置" title="画像规则" pill="规则上下文" description="按课程上下文维护画像阈值、权重和策略模板，确保规则解释口径统一。" />

    <section class="admin-persona-page__panel">
      <section class="admin-persona-step-card">
        <div class="admin-persona-step-card__header">
          <div>
            <div class="admin-persona-step-card__eyebrow">第 1 步</div>
            <div class="admin-persona-step-card__title">规则上下文</div>
            <div class="admin-persona-step-card__desc">先选择当前规则适用的学科与年级，后续阈值、策略模板和画像结果都基于这个上下文。</div>
          </div>
          <div class="admin-persona-step-card__badge">当前编辑</div>
        </div>
        <div class="admin-context">
          <label class="admin-context__field">
            <span>学科</span>
            <el-input v-model="personaSubject" placeholder="学科，例如：计算机网络" />
          </label>
          <label class="admin-context__field">
            <span>年级 / 规则层级</span>
            <el-input v-model="personaGrade" placeholder="层级，例如：通用" />
          </label>
        </div>
      </section>
      <AdminPersonaManager :subject="personaSubject" :grade="personaGrade" />
    </section>
  </div>
</template>

<style scoped>
.admin-persona-page {
  display: grid;
  gap: 20px;
}

.admin-persona-page__panel {
  display: grid;
  gap: 16px;
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.admin-persona-step-card {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  border: 1px solid #dfe9f7;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
}

.admin-persona-step-card__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.admin-persona-step-card__eyebrow {
  font-size: 12px;
  font-weight: 800;
  color: #6b86aa;
}

.admin-persona-step-card__title {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 800;
  color: #183153;
}

.admin-persona-step-card__desc {
  margin-top: 8px;
  max-width: 640px;
  font-size: 14px;
  line-height: 1.7;
  color: #6c7f99;
}

.admin-persona-step-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #dce8f7;
  background: #f3f8ff;
  color: #37537d;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.admin-context {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr 1fr;
}

.admin-context__field {
  display: grid;
  gap: 8px;
}

.admin-context__field span {
  font-size: 13px;
  font-weight: 700;
  color: #516d90;
}

@media (max-width: 900px) {
  .admin-persona-step-card__header {
    flex-direction: column;
  }

  .admin-context {
    grid-template-columns: 1fr;
  }
}
</style>
