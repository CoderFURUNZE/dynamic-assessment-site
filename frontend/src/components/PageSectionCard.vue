<script setup lang="ts">
defineProps<{
  eyebrow?: string;
  title: string;
  description?: string;
}>();
</script>

<template>
  <section class="page-section-card panel-card">
    <header class="page-section-card__header">
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
  padding: 18px;
}

.page-section-card__header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--app-border);
}

.page-section-card__main {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.page-section-card__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b84aa;
}

.page-section-card__title {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  font-weight: 800;
  color: var(--app-ink);
}

.page-section-card__description {
  margin: 0;
  max-width: 640px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-ink-soft);
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
    grid-template-columns: 1fr;
    align-items: start;
    gap: 12px;
  }

  .page-section-card__title {
    font-size: 18px;
  }

  .page-section-card__actions {
    justify-content: flex-start;
  }
}
</style>
