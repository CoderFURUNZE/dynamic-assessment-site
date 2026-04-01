<script setup lang="ts">
defineProps<{
  profile: any;
  currentStage: any | null;
  hasStageModel: boolean;
}>();
</script>

<template>
  <section class="report-hero">
    <div class="hero-label">当前结果</div>
    <div class="hero-title">{{ profile.persona_label }}</div>
    <div class="hero-stage">
      <span>{{ currentStage?.stage_title || "尚未形成阶段评价" }}</span>
      <el-tag v-if="currentStage" size="small" effect="dark">{{ currentStage.trend_label }}</el-tag>
    </div>
    <div class="hero-text">{{ currentStage?.reason_summary || profile.reason_summary }}</div>
    <div class="hero-metrics">
      <div class="hero-metric">
        <span>课程掌握度</span>
        <strong>{{ Math.round(profile.course_mastery * 100) }}%</strong>
      </div>
      <div class="hero-metric">
        <span>动态评分</span>
        <strong>{{ Math.round(profile.dynamic_score * 100) }}%</strong>
      </div>
      <div class="hero-metric">
        <span>{{ hasStageModel ? "阶段等级" : "稳定性" }}</span>
        <strong>{{ hasStageModel ? currentStage?.risk_level || profile.risk_level : `${Math.round(profile.stability * 100)}%` }}</strong>
      </div>
      <div class="hero-metric">
        <span>当前状态</span>
        <strong>{{ profile.risk_level }}</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.report-hero {
  padding: 18px 20px;
  border-radius: 20px;
  background: #ffffff;
  color: var(--app-ink);
  display: grid;
  gap: 10px;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.hero-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #6f85a3;
  text-transform: uppercase;
}

.hero-title {
  font-size: 28px;
  font-weight: 800;
}

.hero-stage {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #5e7697;
}

.hero-text {
  line-height: 1.65;
  font-size: 13px;
  color: var(--app-ink-soft);
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.hero-metric {
  padding: 12px 14px;
  border-radius: 16px;
  background: #fcfdff;
  display: grid;
  gap: 4px;
  border: 1px solid var(--app-border);
}

.hero-metric span {
  font-size: 12px;
  color: #6b809c;
}

.hero-metric strong {
  font-size: 22px;
  font-weight: 800;
  color: var(--app-ink);
}
</style>
