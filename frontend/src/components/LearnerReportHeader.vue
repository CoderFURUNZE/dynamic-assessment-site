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
      <div class="report-header__eyebrow">Learning Report</div>
      <div class="report-title">我的学习情况</div>
      <div class="report-subtitle">这里会告诉你现在学得怎么样、哪里学得好、下一步该做什么。</div>
    </div>
    <el-button size="small" @click="emit('refresh')" :loading="loading">刷新</el-button>
  </div>
</template>

<style scoped>
.report-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.report-header__main {
  display: grid;
  gap: 6px;
}

.report-header__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6c86ab;
}

.report-title {
  font-size: 24px;
  line-height: 1.2;
  font-weight: 800;
  color: #22395b;
}

.report-subtitle {
  max-width: 720px;
  margin-top: 2px;
  font-size: 13px;
  line-height: 1.7;
  color: #667d9b;
}

@media (max-width: 960px) {
  .report-header {
    align-items: flex-start;
  }
}
</style>
