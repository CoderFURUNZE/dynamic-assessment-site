<script setup lang="ts">
type CourseOption = {
  id: number;
  title: string;
};

withDefaults(
  defineProps<{
    eyebrow?: string;
    title: string;
    description?: string;
    pill?: string;
    fieldLabel?: string;
    placeholder?: string;
    modelValue?: string;
    courses?: CourseOption[];
  }>(),
  {
    eyebrow: "教师工作台",
    description: "",
    pill: "",
    fieldLabel: "当前课程",
    placeholder: "请选择课程",
    modelValue: "",
    courses: () => [],
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();
</script>

<template>
  <section class="teacher-workspace-hero">
    <div class="teacher-workspace-hero__copy">
      <span class="teacher-workspace-hero__eyebrow">{{ eyebrow }}</span>
      <div class="teacher-workspace-hero__headline">
        <h1>{{ title }}</h1>
        <span v-if="pill" class="teacher-workspace-hero__pill">{{ pill }}</span>
      </div>
      <p v-if="description" class="teacher-workspace-hero__desc">{{ description }}</p>
      <div v-if="$slots.meta" class="teacher-workspace-hero__meta">
        <slot name="meta" />
      </div>
    </div>

    <div class="teacher-workspace-hero__panel">
      <div class="teacher-workspace-hero__field">
        <label>{{ fieldLabel }}</label>
        <el-select
          :model-value="modelValue"
          class="teacher-workspace-hero__select"
          size="large"
          :placeholder="placeholder"
          @update:model-value="emit('update:modelValue', String($event || ''))"
        >
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
      </div>

      <div v-if="$slots.actions" class="teacher-workspace-hero__actions">
        <slot name="actions" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.teacher-workspace-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 18px;
  padding: 20px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    radial-gradient(circle at top left, rgba(219, 234, 254, 0.26), transparent 26%),
    radial-gradient(circle at right top, rgba(220, 252, 231, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow:
    0 14px 32px rgba(15, 23, 42, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.teacher-workspace-hero__copy {
  display: grid;
  align-content: start;
  gap: 10px;
  min-width: 0;
}

.teacher-workspace-hero__eyebrow {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(34, 197, 94, 0.18);
  background: #eefbf3;
  color: #166534;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.teacher-workspace-hero__headline {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.teacher-workspace-hero__headline h1 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(24px, 3.2vw, 36px);
  line-height: 1.08;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.teacher-workspace-hero__pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.teacher-workspace-hero__desc {
  margin: 0;
  max-width: 58ch;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.teacher-workspace-hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.teacher-workspace-hero__panel {
  display: grid;
  gap: 12px;
  align-content: start;
  min-width: 0;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(219, 234, 254, 0.16), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 250, 252, 0.92) 100%);
}

.teacher-workspace-hero__field {
  display: grid;
  gap: 8px;
}

.teacher-workspace-hero__field label {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.teacher-workspace-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__select .el-select__wrapper) {
  min-height: 42px;
  border-radius: 14px;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.22) inset !important;
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__select .el-select__selected-item),
.teacher-workspace-hero :deep(.teacher-workspace-hero__select .el-select__placeholder) {
  color: #475569;
  font-weight: 700;
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .el-button),
.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .hint-button) {
  min-height: 40px;
  padding-inline: 14px;
  border-radius: 12px;
  border-width: 1px;
  font-weight: 700;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .el-button:not(.el-button--primary)),
.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .hint-button:not(.el-button--primary)) {
  background: #ffffff !important;
  border-color: rgba(148, 163, 184, 0.22) !important;
  color: #475569 !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .el-button--primary) {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
  border-color: rgba(34, 197, 94, 0.24) !important;
  color: #ffffff !important;
  box-shadow: 0 12px 20px rgba(15, 23, 42, 0.08);
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .el-button:hover),
.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .hint-button:hover) {
  transform: translateY(-1px);
}

.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .el-button:focus-visible),
.teacher-workspace-hero :deep(.teacher-workspace-hero__actions .hint-button:focus-visible),
.teacher-workspace-hero :deep(.teacher-workspace-hero__select .el-select__wrapper.is-focused) {
  outline: none;
  box-shadow:
    0 0 0 4px rgba(96, 165, 250, 0.14),
    0 10px 22px rgba(96, 165, 250, 0.16) !important;
}

@media (max-width: 900px) {
  .teacher-workspace-hero {
    grid-template-columns: 1fr;
    padding: 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .teacher-workspace-hero :deep(.teacher-workspace-hero__actions .el-button),
  .teacher-workspace-hero :deep(.teacher-workspace-hero__actions .hint-button) {
    transition: none;
  }
}
</style>
