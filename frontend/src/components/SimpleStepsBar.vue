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
  gap: 12px;
  border-radius: calc(var(--app-radius) - 2px);
  background: #ffffff;
  border: 1px solid var(--app-border);
  color: var(--app-ink);
  min-height: 64px;
  box-shadow: none;
}

.simple-steps-bar__item strong {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: inline-grid;
  place-items: center;
  background: #eef4ff;
  color: var(--app-green-dark);
  font-size: 14px;
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
