<script setup lang="ts">
const props = defineProps<{
  modelValue: string;
  courses: Array<{ id: number; title: string; code?: string }>;
  badge: string;
  title: string;
  subtitle?: string;
  metaText?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
  (e: "change", value: string): void;
}>();

function handleChange(value: string) {
  emit("update:modelValue", value);
  emit("change", value);
}
</script>

<template>
  <el-card class="panel-card workspace-topbar" shadow="never">
    <div class="workspace-topbar__content">
      <div class="workspace-topbar__main">
        <div class="workspace-topbar__badge">{{ badge }}</div>
        <div class="workspace-topbar__title">{{ title }}</div>
        <div v-if="subtitle" class="workspace-topbar__subtitle">{{ subtitle }}</div>
      </div>

      <div class="workspace-topbar__actions">
        <el-select
          :model-value="modelValue"
          size="small"
          class="workspace-topbar__select"
          placeholder="选择课程"
          @update:model-value="handleChange"
        >
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <slot />
      </div>
    </div>
    <div v-if="metaText" class="workspace-topbar__meta">{{ metaText }}</div>
  </el-card>
</template>

<style scoped>
.workspace-topbar {
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  box-shadow: none;
  background: #ffffff;
  overflow: hidden;
}

.workspace-topbar__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 16px;
  padding: 16px 18px 14px;
}

.workspace-topbar__main {
  display: grid;
  gap: 4px;
  flex: 1;
  min-width: 260px;
}

.workspace-topbar__badge {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--app-ink-soft);
  font-weight: 800;
  background: rgba(79, 140, 255, 0.08);
  padding: 4px 10px;
  border-radius: 999px;
  width: fit-content;
  border: 1px solid var(--app-border);
}

.workspace-topbar__title {
  font-size: 22px;
  line-height: 1.15;
  font-weight: 800;
  color: var(--app-ink);
  letter-spacing: -0.01em;
}

.workspace-topbar__subtitle {
  max-width: 620px;
  color: var(--app-ink-soft);
  line-height: 1.6;
  font-size: 13px;
}

.workspace-topbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.workspace-topbar__select {
  width: 280px;
}

.workspace-topbar__meta {
  margin-top: 0;
  color: var(--app-ink-soft);
  font-size: 12px;
  padding: 10px 18px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--app-border);
  background: #fbfcfe;
}

.workspace-topbar__meta::before {
  content: '';
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--app-green);
}

@media (max-width: 960px) {
  .workspace-topbar__content {
    grid-template-columns: 1fr;
    padding: 14px 16px 12px;
  }
  
  .workspace-topbar__title {
    font-size: 20px;
  }

  .workspace-topbar__select {
    width: 100%;
  }

  .workspace-topbar__actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .workspace-topbar__meta {
    padding: 10px 16px 12px;
  }
}

@media (max-width: 768px) {
  .workspace-topbar__content {
    padding: 12px 14px 10px;
    gap: 12px;
  }
  
  .workspace-topbar__title {
    font-size: 18px;
  }
  
  .workspace-topbar__meta {
    padding: 8px 14px 10px;
  }
}
</style>
