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
  border-radius: 28px;
  border: 3px solid #1f2937;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  background: linear-gradient(180deg, #fff8ef 0%, #fffdf8 100%);
  overflow: hidden;
}

.workspace-topbar__content {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 16px;
  padding: 14px 18px 12px;
}

.workspace-topbar__icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: #355070;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.86);
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
  text-transform: uppercase;
  color: #1f2937;
  font-weight: 800;
  background: #d7f9a8;
  padding: 5px 10px;
  border-radius: 999px;
  width: fit-content;
  border: 0;
}

.workspace-topbar__title {
  font-size: 24px;
  line-height: 1.1;
  font-weight: 800;
  color: #16355c;
  letter-spacing: -0.03em;
}

.workspace-topbar__subtitle {
  font-size: 13px;
  line-height: 1.6;
  color: #60758f;
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
  min-height: 44px;
  border-radius: 18px !important;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%) !important;
  box-shadow: 0 0 0 1.5px #c6d8ef inset !important;
}

.workspace-topbar__actions :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #7ea9f6 inset, 0 0 0 3px rgba(87, 133, 231, 0.12), 0 12px 24px rgba(80, 118, 183, 0.08) !important;
}

.workspace-topbar__actions :deep(.el-select__placeholder),
.workspace-topbar__actions :deep(.el-select__selected-item),
.workspace-topbar__actions :deep(.el-select__caret) {
  color: #5a6f8f !important;
}

.workspace-topbar__actions :deep(.el-button) {
  min-width: 118px;
  min-height: 44px;
  padding: 0 20px;
  border-radius: 999px !important;
  border: 1.5px solid #c6d8ef !important;
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
  border-color: #96b6e2 !important;
  background: linear-gradient(180deg, #eef5ff 0%, #ffffff 100%) !important;
  background-image: none !important;
  color: #16355c !important;
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
  color: #60758f;
  font-size: 12px;
  padding: 10px 18px 12px;
  display: flex;
  align-items: center;
  gap: var(--app-space-2);
  border-top: 1px solid #cfe0f5;
  background: linear-gradient(180deg, #f5f9ff 0%, #f8fbff 100%);
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
