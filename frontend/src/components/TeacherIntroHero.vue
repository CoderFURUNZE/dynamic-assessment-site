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
  min-height: 116px;
  padding: 22px 24px;
  gap: 18px;
  flex-wrap: wrap;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 20px;
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.08), transparent 26%),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 26%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
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
  color: #166534;
  display: inline-flex;
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  background: #eefbf3;
  border: 1px solid rgba(34, 197, 94, 0.16);
}

.teacher-intro-hero__title {
  margin: 0;
  font-size: 22px;
  line-height: 1.15;
  color: #0f172a;
  font-family: var(--el-font-family);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.teacher-intro-hero__pill {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.teacher-intro-hero__description {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
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
