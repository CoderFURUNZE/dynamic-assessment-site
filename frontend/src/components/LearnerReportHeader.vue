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
      <div class="report-header__eyebrow">操作系统</div>
      <div class="report-title">按课程查看阶段结果与学习建议</div>
    </div>

    <div class="report-header__aside">
      <p>把课程表现、阶段变化和建议放在一个区域里，避免多层切换。</p>
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
  background: #d7f9a8;
  color: #1f2937;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.report-title {
  font-size: clamp(24px, 3vw, 40px);
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #16355c;
}

.report-header__aside {
  display: grid;
  justify-items: end;
  gap: 12px;
  max-width: 420px;
}

.report-header__aside p {
  margin: 0;
  color: #61738b;
  line-height: 1.6;
  text-align: right;
}

.report-header__aside :deep(.el-button) {
  min-height: 44px;
  padding-inline: 18px;
  border-radius: 16px;
  border: 1.5px solid #bfd1eb;
  background: #f8fbff;
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
