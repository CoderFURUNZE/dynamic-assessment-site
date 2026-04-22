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
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(219, 234, 254, 0.36), transparent 28%),
    radial-gradient(circle at left bottom, rgba(220, 252, 231, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  color: #0f172a;
  display: grid;
  gap: 16px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
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
  color: #166534;
  font-weight: 700;
}

.hero-title {
  font-size: clamp(26px, 3.8vw, 36px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  font-weight: 800;
  color: #0f172a;
}

.hero-tag {
  border: 1px solid rgba(34, 197, 94, 0.18);
  background: #eefbf3;
  color: #166534;
}

.hero-stage {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  color: #64748b;
  line-height: 1.6;
}

.hero-stage__label {
  font-weight: 800;
}

.hero-text {
  color: #64748b;
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
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  display: grid;
  gap: 10px;
  align-content: center;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
}

.hero-metric span {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.hero-metric strong {
  font-size: 20px;
  color: #0f172a;
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
