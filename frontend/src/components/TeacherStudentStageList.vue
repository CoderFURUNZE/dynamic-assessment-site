<script setup lang="ts">
defineProps<{
  stageHistory: any[];
  selectedStageId: number | null;
}>();

const emit = defineEmits<{
  (e: "select", stageId: number): void;
}>();

function tagType(label: string) {
  if (label === "进步") return "success";
  if (label === "退步") return "danger";
  return "info";
}
</script>

<template>
  <section class="panel-card soft-card">
    <div class="soft-title">阶段变化</div>
    <div v-if="stageHistory.length" class="stage-list">
      <button
        v-for="item in stageHistory"
        :key="item.stage_id"
        type="button"
        class="stage-item"
        :class="{ 'stage-item--active': item.stage_id === selectedStageId }"
        @click="emit('select', item.stage_id)"
      >
        <div class="stage-item__top">
          <span>阶段 {{ item.stage_order }}</span>
          <el-tag size="small" :type="tagType(item.trend_label)">
            {{ item.trend_label }}
          </el-tag>
        </div>
        <div class="stage-item__title">{{ item.stage_title }}</div>
        <div class="stage-item__meta">
          <span>{{ item.persona_label }}</span>
          <span>{{ Math.round((item.dynamic_score || 0) * 100) }}%</span>
        </div>
      </button>
    </div>
    <div v-else class="empty-help">
      <el-empty description="当前还没有阶段评价数据" />
      <div class="empty-help__text">请先在教师端创建阶段，并为这门课导入阶段数据，系统才会生成这里的结果。</div>
    </div>
  </section>
</template>

<style scoped>
.soft-card {
  border-radius: 20px;
}

.soft-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
  margin-bottom: 12px;
}

.stage-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.stage-item {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: #fcfdff;
  display: grid;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.stage-item:hover,
.stage-item--active {
  border-color: #bfd3ea;
  box-shadow: var(--app-shadow-soft);
  transform: translateY(-1px);
}

.stage-item__top,
.stage-item__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.stage-item__top {
  font-size: 12px;
  color: #567290;
}

.stage-item__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-ink);
}

.stage-item__meta {
  font-size: 12px;
  color: #66809a;
}

.empty-help {
  display: grid;
  gap: 8px;
  align-content: start;
}

.empty-help__text {
  font-size: 12px;
  line-height: 1.7;
  color: var(--app-ink-soft);
  text-align: center;
}
</style>
