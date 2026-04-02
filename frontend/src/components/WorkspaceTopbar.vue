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
  box-shadow: var(--app-shadow-soft);
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
  background: color-mix(in srgb, var(--app-primary) 8%, transparent);
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

.workspace-topbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;
}

.workspace-topbar__select {
  width: 280px;
  max-width: 100%;
}

.workspace-topbar__actions :deep(.el-select__wrapper) {
  min-height: 42px;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px #d7e4f5 inset !important;
}

.workspace-topbar__actions :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #7ea9f6 inset, 0 0 0 3px rgba(87, 133, 231, 0.12) !important;
}

.workspace-topbar__actions :deep(.el-select__placeholder),
.workspace-topbar__actions :deep(.el-select__selected-item),
.workspace-topbar__actions :deep(.el-select__caret) {
  color: #5a6f8f !important;
}

.workspace-topbar__actions :deep(.el-button) {
  min-width: 118px;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px !important;
  border: 1px solid #d7e4f5 !important;
  background: #ffffff !important;
  background-image: none !important;
  color: #274263 !important;
  font-size: 14px;
  font-weight: 700;
  box-shadow: none !important;
}

.workspace-topbar__actions :deep(.el-button:hover),
.workspace-topbar__actions :deep(.el-button:focus-visible) {
  border-color: #9fbef3 !important;
  background: #f8fbff !important;
  background-image: none !important;
  color: #214d8f !important;
}

.workspace-topbar__actions :deep(.el-button--primary) {
  border-color: #b8cdf3 !important;
  background: #ffffff !important;
  background-image: none !important;
  color: #2e5ea8 !important;
}

.workspace-topbar__actions :deep(.el-button.is-disabled),
.workspace-topbar__actions :deep(.el-button.is-disabled:hover) {
  border-color: #e3eaf5 !important;
  background: #f8fbff !important;
  background-image: none !important;
  color: #afbdd0 !important;
}

.workspace-topbar__meta {
  margin-top: 0;
  color: var(--app-ink-soft);
  font-size: var(--app-text-xs);
  padding: 10px 18px 12px;
  display: flex;
  align-items: center;
  gap: var(--app-space-2);
  border-top: 1px solid var(--app-border);
  background: color-mix(in srgb, var(--app-primary-tint) 45%, var(--app-card));
}

.workspace-topbar__meta::before {
  content: '';
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--app-green);
}

@media (max-width: 1120px) {
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
