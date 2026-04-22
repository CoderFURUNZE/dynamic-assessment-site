<script setup lang="ts">
defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: "refresh"): void;
}>();
</script>

<template>
  <div class="report-header">
    <div class="report-header__main">
      <div class="report-header__eyebrow">学习报告</div>
      <div class="report-title">按课程查看阶段结果与学习建议</div>
    </div>

    <div class="report-header__aside">
      <p>把课程表现、阶段变化和建议集中查看。</p>
      <el-button size="small" @click="emit('refresh')" :loading="loading">刷新</el-button>
    </div>
  </div>
</template>

<style scoped>
.report-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.report-header__main {
  display: grid;
  gap: 8px;
}

.report-header__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eefbf3;
  border: 1px solid rgba(34, 197, 94, 0.18);
  color: #166534;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.report-title {
  font-size: clamp(24px, 3vw, 36px);
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #0f172a;
}

.report-header__aside {
  display: grid;
  justify-items: end;
  gap: 12px;
  max-width: 360px;
}

.report-header__aside p {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
  text-align: right;
}

.report-header__aside :deep(.el-button) {
  min-height: 40px;
  padding-inline: 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
  color: #475569;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.05);
}

@media (max-width: 960px) {
  .report-header__aside {
    justify-items: start;
  }

  .report-header__aside p {
    text-align: left;
  }
}
</style>
