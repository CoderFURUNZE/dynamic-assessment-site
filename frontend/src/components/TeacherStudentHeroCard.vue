<script setup lang="ts">
const props = defineProps<{
  detail: any;
  selectedStage: any | null;
}>();
</script>

<template>
  <section class="hero-card">
    <div class="hero-label">当前情况</div>
    <div class="hero-name">{{ props.detail.student.full_name || props.detail.student.username }}</div>
    <div class="hero-meta">
      {{ props.detail.profile.persona_label }} · {{ props.detail.profile.risk_level }}
      <span v-if="props.detail.profile.current_stage_title">· {{ props.detail.profile.current_stage_title }}</span>
      <span v-if="props.detail.profile.current_stage_trend">· {{ props.detail.profile.current_stage_trend }}</span>
    </div>
    <div class="hero-text">{{ props.selectedStage?.reason_summary || props.detail.profile.reason_summary }}</div>
    <div class="hero-stats">
      <div class="hero-stat">
        <span>动态评分</span>
        <strong>{{ Math.round((props.detail.profile.dynamic_score || 0) * 100) }}%</strong>
      </div>
      <div class="hero-stat">
        <span>课程掌握度</span>
        <strong>{{ Math.round((props.detail.profile.course_mastery || 0) * 100) }}%</strong>
      </div>
      <div class="hero-stat">
        <span>学习投入</span>
        <strong>{{ Math.round(((props.selectedStage?.engagement ?? props.detail.profile.engagement) || 0) * 100) }}%</strong>
      </div>
      <div class="hero-stat">
        <span>学习成效</span>
        <strong>{{ Math.round(((props.selectedStage?.achievement ?? props.detail.profile.achievement) || 0) * 100) }}%</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero-card {
  padding: 22px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
  color: var(--app-ink);
  display: grid;
  gap: 10px;
}

.hero-label {
  font-size: 12px;
  color: #5c7da8;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
}

.hero-name {
  font-size: 28px;
  font-weight: 800;
  color: #22395b;
}

.hero-meta {
  font-size: 14px;
  font-weight: 700;
  color: #35577f;
}

.hero-text {
  font-size: 14px;
  line-height: 1.7;
  color: #587596;
}

.hero-stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.hero-stat {
  padding: 12px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: none;
  display: grid;
  gap: 4px;
}

.hero-stat span {
  font-size: 12px;
  color: #6f86a3;
}

.hero-stat strong {
  font-size: 20px;
  font-weight: 800;
  color: #2a4d78;
}

@media (max-width: 1100px) {
  .hero-stats {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .hero-stats {
    grid-template-columns: 1fr;
  }
}
</style>
