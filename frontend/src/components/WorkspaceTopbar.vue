<script setup lang="ts">
import { Compass } from "@element-plus/icons-vue";

const props = defineProps<{
  modelValue: string;
  courses: Array<{ id: number; title: string; code?: string }>;
  badge: string;
  title: string;
  subtitle?: string;
  metaText?: string;
  icon?: any;
  showSelect?: boolean;
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
      <div class="workspace-topbar__icon">
        <el-icon><component :is="props.icon || Compass" /></el-icon>
      </div>
      <div class="workspace-topbar__main">
        <div class="workspace-topbar__badge">{{ badge }}</div>
        <div class="workspace-topbar__title">{{ title }}</div>
        <div v-if="subtitle" class="workspace-topbar__subtitle">{{ subtitle }}</div>
      </div>

      <div class="workspace-topbar__actions">
        <el-select
          v-if="props.showSelect !== false"
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
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.07);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  overflow: hidden;
}

.workspace-topbar__content {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
  padding: 16px 18px 14px;
}

.workspace-topbar__icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #1f2937;
  background: linear-gradient(180deg, #eefbf3 0%, #f8fcff 100%);
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.workspace-topbar__icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.workspace-topbar__main {
  display: grid;
  gap: 3px;
  flex: 1;
  min-width: 260px;
}

.workspace-topbar__badge {
  font-size: 11px;
  color: #166534;
  font-weight: 700;
  background: #eefbf3;
  padding: 4px 10px;
  border-radius: 999px;
  width: fit-content;
  border: 1px solid rgba(34, 197, 94, 0.16);
}

.workspace-topbar__title {
  font-size: 20px;
  line-height: 1.2;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.workspace-topbar__subtitle {
  font-size: 13px;
  line-height: 1.5;
  color: #64748b;
}

.workspace-topbar__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;
}

.workspace-topbar__select {
  width: 280px;
  max-width: 100%;
}

.workspace-topbar__actions :deep(.el-select__wrapper) {
  min-height: 40px;
  border-radius: 12px !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.28) inset !important;
}

.workspace-topbar__actions :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #60a5fa inset, 0 0 0 4px rgba(96, 165, 250, 0.14) !important;
}

.workspace-topbar__actions :deep(.el-select__placeholder),
.workspace-topbar__actions :deep(.el-select__selected-item),
.workspace-topbar__actions :deep(.el-select__caret) {
  color: #6b7280 !important;
}

.workspace-topbar__actions :deep(.el-button) {
  min-width: 104px;
  min-height: 38px;
  padding: 0 16px;
  border-radius: 12px !important;
  border: 1px solid rgba(148, 163, 184, 0.24) !important;
  background: #ffffff !important;
  background-image: none !important;
  color: #334155 !important;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04) !important;
}

.workspace-topbar__actions :deep(.el-button:hover),
.workspace-topbar__actions :deep(.el-button:focus-visible) {
  border-color: rgba(100, 116, 139, 0.34) !important;
  background: #ffffff !important;
  background-image: none !important;
  color: #1f2937 !important;
  box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08) !important;
}

.workspace-topbar__actions :deep(.el-button--primary) {
  border-color: transparent !important;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
  background-image: none !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08) !important;
}

.workspace-topbar__actions :deep(.el-button.is-disabled),
.workspace-topbar__actions :deep(.el-button.is-disabled:hover) {
  border-color: #e3eaf5 !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  background-image: none !important;
  color: #afbdd0 !important;
}

.workspace-topbar__meta {
  margin-top: 0;
  color: #6b7280;
  font-size: 12px;
  padding: 10px 18px 12px;
  display: flex;
  align-items: center;
  gap: var(--app-space-2);
  border-top: 1px solid rgba(148, 163, 184, 0.14);
  background: #fbfdff;
}

.workspace-topbar__meta::before {
  content: "";
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--app-green);
}

@media (max-width: 1120px) {
  .workspace-topbar__content {
    grid-template-columns: auto 1fr;
    padding: 14px 16px 12px;
  }

  .workspace-topbar__title {
    font-size: 19px;
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
    font-size: 17px;
  }

  .workspace-topbar__meta {
    padding: 8px 14px 10px;
  }
}
</style>
