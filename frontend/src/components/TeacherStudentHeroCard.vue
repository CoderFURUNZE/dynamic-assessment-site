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
  padding: 24px;
  border-radius: 30px;
  background: radial-gradient(circle at top right, rgba(210, 238, 255, 0.72), transparent 40%), #fffdf6;
  border: 3px solid #1f2937;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  color: #17325c;
  display: grid;
  gap: 12px;
}

.hero-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: #d7f9a8;
  color: #17325c;
  font-size: 12px;
  font-weight: 800;
}

.hero-name {
  font-size: 34px;
  font-weight: 800;
  color: #17325c;
}

.hero-meta {
  font-size: 14px;
  font-weight: 700;
  color: #4f6788;
}

.hero-text {
  font-size: 14px;
  line-height: 1.7;
  color: #5b6c85;
}

.hero-stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.hero-stat {
  padding: 14px;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #cadcf7;
  box-shadow: none;
  display: grid;
  gap: 4px;
}

.hero-stat span {
  font-size: 12px;
  color: #6f809f;
}

.hero-stat strong {
  font-size: 20px;
  font-weight: 800;
  color: #17325c;
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
