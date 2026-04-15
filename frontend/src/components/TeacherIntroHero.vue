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
  min-height: 124px;
  padding: 20px 24px;
  gap: 18px;
  flex-wrap: wrap;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.3), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
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
  color: #1f2937;
  text-transform: uppercase;
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #d7f9a8;
}

.teacher-intro-hero__title {
  margin: 0;
  font-size: 24px;
  line-height: 1.15;
  color: #1d2433;
  font-family: "Fredoka", "Nunito", sans-serif;
}

.teacher-intro-hero__pill {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  border: 1.5px solid #c6d8ef;
  background: #f6faff;
  color: #29476a;
  font-size: 12px;
  font-weight: 700;
}

.teacher-intro-hero__description {
  margin: 0;
  color: #636b7a;
  font-size: 14px;
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
