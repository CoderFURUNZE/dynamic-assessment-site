<script setup lang="ts">
defineProps<{
  profile: any;
  currentStage: any | null;
  hasStageModel: boolean;
}>();
</script>

<template>
  <section class="report-hero">
    <div class="hero-summary">
      <div class="hero-head">
        <div class="hero-head__copy">
          <div class="hero-label">当前阶段画像</div>
          <div class="hero-title">{{ profile.persona_label }}</div>
        </div>
        <el-tag v-if="currentStage" size="small" round class="hero-tag">{{ currentStage.trend_label }}</el-tag>
      </div>

      <div class="hero-stage">
        <span class="hero-stage__label">阶段</span>
        <span>{{ currentStage?.stage_title || "尚未形成阶段评价" }}</span>
      </div>

      <div class="hero-text">{{ currentStage?.reason_summary || profile.reason_summary }}</div>
    </div>

    <div class="hero-score" :style="{ '--hero-score': `${Math.round(profile.dynamic_score * 100)}%` }">
      <strong>{{ Math.round(profile.dynamic_score * 100) }}%</strong>
      <span>动态评分</span>
    </div>

    <div class="hero-metrics">
      <div class="hero-metric">
        <span>课程掌握度</span>
        <strong>{{ Math.round(profile.course_mastery * 100) }}%</strong>
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
  padding: 22px;
  border-radius: 18px;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.12), transparent 30%),
    radial-gradient(circle at 0% 100%, rgba(34, 197, 94, 0.14), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
  color: #0f172a;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px minmax(260px, 0.9fr);
  gap: 20px;
  align-items: center;
  border: 1px solid rgba(99, 120, 153, 0.2);
  box-shadow: 0 18px 38px rgba(20, 35, 58, 0.08);
}

.hero-summary {
  display: grid;
  gap: 14px;
  min-width: 0;
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
  font-weight: 800;
}

.hero-title {
  font-size: clamp(26px, 3.8vw, 36px);
  line-height: 1.08;
  font-weight: 800;
  color: #0f172a;
  overflow-wrap: break-word;
}

.hero-tag {
  border: 1px solid rgba(34, 197, 94, 0.18);
  background: #eefbf3;
  color: #166534;
}

.hero-stage {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #52647a;
  line-height: 1.6;
}

.hero-stage__label {
  font-weight: 800;
}

.hero-text {
  color: #52647a;
  line-height: 1.7;
  font-size: 14px;
}

.hero-score {
  width: 132px;
  height: 132px;
  justify-self: center;
  border-radius: 999px;
  display: grid;
  place-items: center;
  align-content: center;
  background: conic-gradient(#22c55e var(--hero-score), #dbeafe 0);
  box-shadow: inset 0 0 0 10px #ffffff, 0 16px 28px rgba(34, 197, 94, 0.16);
}

.hero-score strong {
  font-size: 30px;
  color: #102033;
}

.hero-score span {
  font-size: 12px;
  color: #52647a;
  font-weight: 800;
}

.hero-metrics {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.hero-metric {
  min-height: 76px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(99, 120, 153, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  display: grid;
  gap: 6px;
  align-content: center;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
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

@media (max-width: 980px) {
  .report-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hero-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
