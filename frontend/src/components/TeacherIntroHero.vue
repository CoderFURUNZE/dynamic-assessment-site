<script setup lang="ts">
defineProps<{
  eyebrow?: string;
  title: string;
  description?: string;
  pill?: string;
}>();
</script>

<template>
  <section class="teacher-intro-hero panel-card">
    <div class="teacher-intro-hero__main">
      <p v-if="eyebrow" class="teacher-intro-hero__eyebrow">{{ eyebrow }}</p>
      <div class="teacher-intro-hero__row">
        <h2 class="teacher-intro-hero__title">{{ title }}</h2>
        <span v-if="pill" class="teacher-intro-hero__pill">{{ pill }}</span>
      </div>
      <p v-if="description" class="teacher-intro-hero__description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="teacher-intro-hero__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<style scoped>
.teacher-intro-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 108px;
  padding: 14px 22px;
  gap: 16px;
  flex-wrap: wrap;
  border-color: #cddcf3;
  background:
    radial-gradient(circle at top right, rgba(112, 164, 255, 0.28), transparent 38%),
    linear-gradient(135deg, #eef5ff 0%, #e8f1ff 56%, #f5f9ff 100%);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
}

.teacher-intro-hero__main {
  display: grid;
  gap: 5px;
  max-width: 680px;
}

.teacher-intro-hero__row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.teacher-intro-hero__eyebrow {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #4f6f9e;
  text-transform: uppercase;
}

.teacher-intro-hero__title {
  margin: 0;
  font-size: 20px;
  line-height: 1.15;
  color: #1f2d3d;
}

.teacher-intro-hero__pill {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  border: 1px solid #d7e4f5;
  background: linear-gradient(180deg, #ffffff 0%, #f6faff 100%);
  color: #4f6788;
  font-size: 12px;
  font-weight: 700;
}

.teacher-intro-hero__description {
  margin: 0;
  color: #61789a;
  font-size: 13px;
  line-height: 1.65;
}

.teacher-intro-hero__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  margin-left: auto;
}

@media (max-width: 960px) {
  .teacher-intro-hero {
    padding: 14px 18px;
  }

  .teacher-intro-hero__actions {
    margin-left: 0;
    width: 100%;
  }
}
</style>
