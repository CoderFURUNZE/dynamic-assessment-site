<script setup lang="ts">
import { Grid } from "@element-plus/icons-vue";

defineProps<{
  eyebrow?: string;
  title: string;
  description?: string;
  icon?: any;
}>();
</script>

<template>
  <section class="page-section-card panel-card">
    <header class="page-section-card__header">
      <div class="page-section-card__icon">
        <el-icon><component :is="icon || Grid" /></el-icon>
      </div>
      <div class="page-section-card__main">
        <div v-if="eyebrow" class="page-section-card__eyebrow">{{ eyebrow }}</div>
        <h2 class="page-section-card__title">{{ title }}</h2>
        <p v-if="description" class="page-section-card__description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="page-section-card__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="page-section-card__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.page-section-card {
  padding: 18px 20px;
}

.page-section-card__header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  align-items: start;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--app-border);
}

.page-section-card__icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--app-primary-deep);
  background: linear-gradient(135deg, rgba(74, 132, 255, 0.12) 0%, rgba(107, 197, 255, 0.12) 100%);
  border: 1px solid color-mix(in srgb, var(--app-primary) 18%, #ffffff);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.page-section-card__icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.page-section-card__main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.page-section-card__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-eyebrow);
}

.page-section-card__title {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  font-weight: 800;
  color: var(--app-ink);
}

.page-section-card__description {
  margin: 0;
  max-width: 560px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--app-ink-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.page-section-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.page-section-card__body {
  min-width: 0;
}

@media (max-width: 900px) {
  .page-section-card {
    padding: 14px;
  }

  .page-section-card__header {
    grid-template-columns: auto 1fr;
    align-items: start;
    gap: 12px;
  }

  .page-section-card__title {
    font-size: 17px;
  }

  .page-section-card__actions {
    justify-content: flex-start;
  }
}
</style>
