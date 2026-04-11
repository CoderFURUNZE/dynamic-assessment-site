<script setup lang="ts">
type TabItem = {
  key: string;
  label: string;
  desc: string;
};

defineProps<{
  eyebrow: string;
  title: string;
  description?: string;
  tabs: TabItem[];
  activeTab: string;
  columns?: 2 | 3 | 4;
  focusLabel?: string;
  focusTitle?: string;
  focusDesc?: string;
}>();

const emit = defineEmits<{
  (event: "change", key: string): void;
}>();
</script>

<template>
  <div class="workspace-hub">
    <section class="workspace-hub__hero">
      <div class="workspace-hub__hero-main">
        <p class="workspace-hub__eyebrow">{{ focusLabel || eyebrow }}</p>
      <div class="workspace-hub__hero-row">
        <h2 class="workspace-hub__hero-title">{{ focusTitle || title }}</h2>
        <span v-if="eyebrow && focusLabel && focusLabel !== eyebrow" class="workspace-hub__hero-pill">{{ eyebrow }}</span>
      </div>
    </div>
  </section>

    <section class="workspace-hub__tabs" :class="`workspace-hub__tabs--${columns || 3}`">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="workspace-hub__tab"
        :class="{ active: activeTab === tab.key }"
        @click="emit('change', tab.key)"
      >
        <strong>{{ tab.label }}</strong>
        <span>{{ tab.desc }}</span>
      </button>
    </section>

    <slot />
  </div>
</template>

<style scoped>
.workspace-hub {
  display: grid;
  gap: 18px;
}

.workspace-hub__hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  border-radius: 24px;
  border: 1px solid #cddcf3;
  background:
    radial-gradient(circle at top right, rgba(112, 164, 255, 0.28), transparent 38%),
    linear-gradient(135deg, #eef5ff 0%, #e8f1ff 56%, #f5f9ff 100%);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
}

.workspace-hub__hero-main {
  display: grid;
  gap: 5px;
  max-width: 680px;
}

.workspace-hub__eyebrow {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b7d91;
}

.workspace-hub__hero-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.workspace-hub__hero-title {
  margin: 0;
  font-size: 20px;
  color: #1f2d3d;
  line-height: 1.15;
}

.workspace-hub__hero-pill {
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

.workspace-hub__tabs {
  display: grid;
  gap: 12px;
}

.workspace-hub__tabs--2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workspace-hub__tabs--3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.workspace-hub__tabs--4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.workspace-hub__tab {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  text-align: left;
  border-radius: 18px;
  border: 1px solid #dfe7f1;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.workspace-hub__tab strong {
  font-size: 15px;
  color: var(--app-text-main);
}

.workspace-hub__tab span {
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-text-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.workspace-hub__tab:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(31, 51, 84, 0.07);
}

.workspace-hub__tab.active {
  border-color: color-mix(in srgb, var(--app-primary) 35%, var(--app-border));
  background: var(--app-primary-tint);
}

@media (max-width: 1100px) {
  .workspace-hub__tabs--4,
  .workspace-hub__tabs--3 {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .workspace-hub__tabs--4,
  .workspace-hub__tabs--3,
  .workspace-hub__tabs--2 {
    grid-template-columns: 1fr;
  }

  .workspace-hub__hero {
    padding: 14px 18px;
  }
}
</style>
