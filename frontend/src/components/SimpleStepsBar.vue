<script setup lang="ts">
defineProps<{
  items: string[];
}>();
</script>

<template>
  <div class="simple-steps-bar">
    <div v-for="(item, index) in items" :key="`${index}-${item}`" class="simple-steps-bar__item">
      <strong>{{ index + 1 }}</strong>
      <span>{{ item }}</span>
    </div>
  </div>
</template>

<style scoped>
.simple-steps-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.simple-steps-bar__item {
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: var(--app-space-3);
  border-radius: calc(var(--app-radius) - 2px);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  color: var(--app-ink);
  min-height: 64px;
  box-shadow: var(--app-shadow-soft);
}

.simple-steps-bar__item strong {
  width: 34px;
  height: 34px;
  border-radius: var(--app-radius-sm);
  display: inline-grid;
  place-items: center;
  background: var(--app-primary-tint);
  color: var(--app-green-dark);
  font-size: var(--app-text-base);
  flex-shrink: 0;
}

.simple-steps-bar__item span {
  line-height: 1.5;
  font-weight: 700;
  font-size: 14px;
}

@media (max-width: 980px) {
  .simple-steps-bar {
    grid-template-columns: 1fr;
  }
}
</style>
