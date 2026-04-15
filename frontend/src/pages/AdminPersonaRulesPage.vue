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
  padding: 18px;
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.admin-persona-step-card {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
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
  color: #25645b;
}

.admin-persona-step-card__title {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 800;
  color: #18463e;
}

.admin-persona-step-card__desc {
  margin-top: 8px;
  max-width: 640px;
  font-size: 14px;
  line-height: 1.7;
  color: #5d746c;
}

.admin-persona-step-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: #eef5ff;
  color: #355070;
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
  color: #4f6c61;
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
