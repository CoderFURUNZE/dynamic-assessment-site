<script setup lang="ts">
defineProps<{
  profile: any;
  currentStage: any | null;
  hasStageModel: boolean;
}>();
</script>

<template>
  <section class="report-hero">
    <div class="hero-head">
      <div class="hero-head__copy">
        <div class="hero-label">当前结果</div>
        <div class="hero-title">{{ profile.persona_label }}</div>
      </div>
      <el-tag v-if="currentStage" size="small" round class="hero-tag">{{ currentStage.trend_label }}</el-tag>
    </div>

    <div class="hero-stage">
      <span class="hero-stage__label">阶段：</span>
      <span>{{ currentStage?.stage_title || "尚未形成阶段评价" }}</span>
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
  padding: 20px 22px;
  border-radius: 34px;
  background: linear-gradient(180deg, #fffdfa 0%, #ffffff 100%);
  color: #1f2937;
  display: grid;
  gap: 16px;
  border: 3px solid #1f2937;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.hero-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.hero-head__copy {
  display: grid;
  gap: 6px;
}

.hero-label {
  font-size: 12px;
  color: #5f7ea3;
  font-weight: 800;
}

.hero-title {
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  font-weight: 800;
  color: #16355c;
}

.hero-tag {
  border: 1.5px solid #b6cae6;
  background: #eef5ff;
  color: #355070;
}

.hero-stage {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  color: #537095;
  line-height: 1.6;
}

.hero-stage__label {
  font-weight: 800;
}

.hero-text {
  color: #537095;
  line-height: 1.7;
  font-size: 14px;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.hero-metric {
  min-height: 98px;
  padding: 18px 20px;
  border-radius: 22px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f8fbff 0%, #fdfefe 100%);
  display: grid;
  gap: 10px;
  align-content: center;
}

.hero-metric span {
  font-size: 12px;
  color: #5f7ea3;
  font-weight: 800;
}

.hero-metric strong {
  font-size: 20px;
  color: #0f2d53;
  font-weight: 800;
}

@media (max-width: 720px) {
  .hero-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
