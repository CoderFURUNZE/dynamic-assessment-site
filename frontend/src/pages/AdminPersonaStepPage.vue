<script setup lang="ts">
import { computed } from "vue";
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";

const props = defineProps<{ mode: "settings" | "results" }>();

const platformTemplateSubject = "平台默认模板";
const platformTemplateGrade = "通用";

const pageItems = [
  { key: "settings", title: "默认画像模板", eyebrow: "模板设置" },
  { key: "results", title: "默认画像模板", eyebrow: "模板设置" },
] as const;

const currentPage = computed(() => pageItems.find((item) => item.key === props.mode) ?? pageItems[0]);
</script>

<template>
  <div class="admin-persona-page">
    <AdminIntroHero
      eyebrow="评价配置"
      title="画像规则模板"
      description="管理员维护平台默认模板，老师在具体课程中选择、复用和微调。"
    />

    <section class="admin-persona-step-card">
      <div class="admin-persona-step-card__header">
        <div>
          <div class="admin-persona-step-card__eyebrow">{{ currentPage.eyebrow }}</div>
          <div class="admin-persona-step-card__title">{{ currentPage.title }}</div>
        </div>
        <div class="admin-persona-step-card__badge">平台默认</div>
      </div>

      <div class="admin-persona-step-card__content">
        <AdminPersonaManager
          :subject="platformTemplateSubject"
          :grade="platformTemplateGrade"
          :step="props.mode"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-persona-page {
  display: grid;
  gap: 20px;
}

.admin-persona-step-card {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  background: #ffffff;
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
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
  color: #2563eb;
}

.admin-persona-step-card__title {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
}

.admin-persona-step-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.admin-persona-step-card__content {
  padding-top: 4px;
}

.admin-persona-step-card__content :deep(.persona-card) {
  border-radius: 22px;
}

@media (max-width: 960px) {
  .admin-persona-step-card__header {
    flex-direction: column;
  }
}
</style>
