<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";

type IndicatorItem = {
  id: number;
  code: string;
  title: string;
  description: string;
  source_type: string;
  default_weight: number;
  active: boolean;
  selected: boolean;
  enabled: boolean;
  weight: number;
};

type DimensionItem = {
  id: number;
  code: string;
  title: string;
  description: string;
  active: boolean;
  indicators: IndicatorItem[];
};

const props = defineProps<{
  courseId: number | null;
  subject: string;
  courses: Array<{ id: number; title: string; code?: string }>;
}>();

const emit = defineEmits<{
  (e: "subject-change", value: string): void;
}>();

const loading = ref(false);
const saving = ref(false);
const items = ref<DimensionItem[]>([]);
const selectedDimensionId = ref<number | null>(null);
const sourceFilter = ref<"all" | "auto" | "imported" | "teacher" | "questionnaire">("all");
const statusFilter = ref<"all" | "enabled" | "disabled">("all");

const sourceTypeOptions = [
  { value: "auto", label: "系统自动" },
  { value: "imported", label: "阶段导入" },
  { value: "teacher", label: "教师补充" },
  { value: "questionnaire", label: "问卷自评" },
] as const;

const selectedDimension = computed(
  () => items.value.find((item) => item.id === selectedDimensionId.value) ?? items.value[0] ?? null,
);

const selectedDimensionSummary = computed(() => {
  const dimension = selectedDimension.value;
  if (!dimension) return { enabledCount: 0, total: 0 };
  const enabledIndicators = dimension.indicators.filter((indicator) => indicator.active && indicator.enabled);
  return {
    enabledCount: enabledIndicators.length,
    total: enabledIndicators.reduce((sum, indicator) => sum + Number(indicator.weight || 0), 0),
  };
});

const filteredIndicators = computed(() => {
  const dimension = selectedDimension.value;
  if (!dimension) return [];
  return dimension.indicators.filter((indicator) => {
    const matchesSource = sourceFilter.value === "all" || indicator.source_type === sourceFilter.value;
    const matchesStatus =
      statusFilter.value === "all" ||
      (statusFilter.value === "enabled" && indicator.enabled) ||
      (statusFilter.value === "disabled" && !indicator.enabled);
    return matchesSource && matchesStatus;
  });
});

function ensureSelectedDimension() {
  if (!items.value.length) {
    selectedDimensionId.value = null;
    return;
  }
  if (!items.value.some((item) => item.id === selectedDimensionId.value)) {
    selectedDimensionId.value = items.value[0].id;
  }
}

function sourceTypeLabel(sourceType: string) {
  if (sourceType === "auto") return "系统自动";
  if (sourceType === "imported") return "阶段导入";
  if (sourceType === "teacher") return "教师补充";
  if (sourceType === "questionnaire") return "问卷自评";
  return sourceType;
}

async function loadSelection() {
  if (!props.courseId) {
    items.value = [];
    selectedDimensionId.value = null;
    return;
  }
  loading.value = true;
  try {
    const res = await api.get(`/portrait/course-selection?course_id=${props.courseId}`);
    items.value = (res.data?.items ?? []).map((dim: DimensionItem) => ({
      ...dim,
      indicators: (dim.indicators ?? []).map((indicator) => ({ ...indicator })),
    }));
    ensureSelectedDimension();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程评价项失败");
  } finally {
    loading.value = false;
  }
}

async function saveSelection() {
  if (!props.courseId) return;
  saving.value = true;
  try {
    const selections = items.value.flatMap((dim) =>
      dim.indicators
        .filter((indicator) => indicator.active)
        .map((indicator) => ({
          indicator_id: indicator.id,
          enabled: indicator.enabled,
          weight: Number(indicator.weight || indicator.default_weight || 0),
        })),
    );
    await api.put(`/portrait/course-selection?course_id=${props.courseId}`, { selections });
    ElMessage.success("课程评价项已保存");
    await loadSelection();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存课程评价项失败");
  } finally {
    saving.value = false;
  }
}

watch(
  () => props.courseId,
  () => {
    selectedDimensionId.value = null;
    sourceFilter.value = "all";
    statusFilter.value = "all";
    loadSelection();
  },
  { immediate: true },
);

watch(
  items,
  () => {
    ensureSelectedDimension();
  },
  { deep: true },
);

onMounted(loadSelection);
</script>

<template>
  <div class="indicator-shell" v-loading="loading">
    <div v-if="!courseId" class="indicator-empty">
      <el-empty description="请先在页面顶部选择一门课程" :image-size="88" />
      <div class="indicator-tip-inline">
        <span>提示</span>
        <HoverTip content="先选择课程，再勾选这门课真正要看的内容。保存后，后面的阶段数据和学生学习情况才会按这些内容计算。" />
      </div>
    </div>

    <div v-else class="indicator-master-wrap">
      <div class="indicator-master">
        <aside class="indicator-master__sidebar">
          <div
            v-for="dimension in items"
            :key="dimension.id"
            class="dimension-card"
            :class="{ 'is-active': selectedDimension?.id === dimension.id }"
            @click="selectedDimensionId = dimension.id"
          >
            <div class="dimension-card__title">{{ dimension.title }}</div>
          </div>
        </aside>

        <section class="indicator-master__detail">
          <div class="indicator-detail-header">
            <div class="indicator-detail-header__main">
              <div class="indicator-detail-header__title">评价维度大类与细类</div>
              <div class="indicator-detail-header__meta">
                {{ selectedDimension ? `${selectedDimension.title}，默认展示该大类下的细项` : "先从左侧选择一个一级维度" }}
              </div>
            </div>
            <div v-if="selectedDimension" class="indicator-toolbar">
              <div class="indicator-toolbar__controls">
                <el-select
                  :model-value="subject"
                  size="large"
                  class="indicator-toolbar__select indicator-toolbar__select--course"
                  placeholder="选择课程"
                  @update:model-value="(value: string | number | boolean | undefined) => emit('subject-change', String(value || ''))"
                >
                  <el-option
                    v-for="course in courses"
                    :key="course.id"
                    :label="course.title"
                    :value="course.title"
                  />
                </el-select>
                <el-select v-model="sourceFilter" size="large" class="indicator-toolbar__select">
                  <el-option label="全部来源" value="all" />
                  <el-option
                    v-for="item in sourceTypeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
                <el-select v-model="statusFilter" size="large" class="indicator-toolbar__select">
                  <el-option label="全部状态" value="all" />
                  <el-option label="仅看启用" value="enabled" />
                  <el-option label="仅看未启用" value="disabled" />
                </el-select>
                <el-button class="indicator-toolbar__save" size="large" round :loading="saving" @click="saveSelection">保存配置</el-button>
              </div>
            </div>
          </div>

          <el-empty
            v-if="!selectedDimension"
            description="当前没有可配置的一级维度"
            :image-size="72"
          />

          <el-empty
            v-else-if="!filteredIndicators.length"
            description="当前筛选条件下没有匹配的细项"
            :image-size="72"
          />

          <div v-else class="indicator-list">
            <article
              v-for="indicator in filteredIndicators"
              :key="indicator.id"
              class="indicator-list__item"
              :class="{ 'is-disabled': !indicator.active }"
            >
              <div class="indicator-list__main">
                <div class="indicator-list__title-row">
                  <el-checkbox v-model="indicator.enabled" :disabled="!indicator.active" size="large">
                    <span class="indicator-list__title">{{ indicator.title }}</span>
                  </el-checkbox>
                  <span class="indicator-list__code">{{ indicator.code }}</span>
                </div>
                <p class="indicator-list__desc">{{ indicator.description || "还没填写说明" }}</p>
              </div>

              <div class="indicator-list__meta">
                <span class="indicator-list__pill indicator-list__pill--source">
                  {{ sourceTypeLabel(indicator.source_type) }}
                </span>
                <span class="indicator-list__pill indicator-list__pill--weight">
                  权重 {{ Number(indicator.weight || 0).toFixed(2) }}
                </span>
                <span
                  class="indicator-list__pill"
                  :class="indicator.active ? 'indicator-list__pill--active' : 'indicator-list__pill--inactive'"
                >
                  {{ indicator.active ? "使用中" : "未启用" }}
                </span>
                <div class="indicator-weight-editor">
                  <span class="indicator-weight-editor__label">比重</span>
                  <el-input-number
                    v-model="indicator.weight"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    size="small"
                    :disabled="!indicator.active"
                  />
                </div>
              </div>
            </article>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.indicator-shell {
  padding: 0;
}

.indicator-shell :deep(.el-card__body) {
  padding-top: 0;
}

.indicator-empty {
  display: grid;
  gap: 14px;
}

.indicator-master-wrap {
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.2), transparent 42%),
    radial-gradient(circle at top left, rgba(187, 247, 208, 0.16), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 18px 36px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.indicator-master {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 18px;
  padding: 20px;
}

.indicator-master__sidebar {
  display: grid;
  align-content: start;
  gap: 12px;
}

.dimension-card {
  min-height: 86px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 18px 18px;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.dimension-card:hover {
  border-color: rgba(59, 130, 246, 0.24);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
}

.dimension-card.is-active {
  border-color: rgba(34, 197, 94, 0.24);
  background: radial-gradient(circle at top left, rgba(187, 247, 208, 0.4), transparent 55%), #ffffff;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
}

.dimension-card__title {
  font-size: 15px;
  font-weight: 800;
  color: #1f2937;
  line-height: 1.5;
}

.indicator-master__detail {
  min-width: 0;
}

.indicator-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 0 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.indicator-detail-header__main {
  min-width: 0;
}

.indicator-detail-header__title {
  font-size: 18px;
  font-weight: 800;
  color: #1f2937;
}

.indicator-detail-header__meta {
  margin-top: 6px;
  font-size: 12px;
  color: #6f809f;
}

.indicator-toolbar {
  min-width: min(100%, 620px);
}

.indicator-toolbar__controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.indicator-toolbar__select {
  width: 148px;
}

.indicator-toolbar__select--course {
  width: 148px;
}

.indicator-toolbar :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 1px rgba(148, 163, 184, 0.2) !important;
}

.indicator-toolbar :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 1px rgba(59, 130, 246, 0.32),
    0 0 0 4px rgba(59, 130, 246, 0.12) !important;
}

.indicator-toolbar :deep(.el-select__selected-item),
.indicator-toolbar :deep(.el-select__placeholder),
.indicator-toolbar :deep(.el-select__caret) {
  color: #5f6f85 !important;
}

.indicator-toolbar :deep(.el-button.indicator-toolbar__save) {
  --el-button-bg-color: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  --el-button-border-color: rgba(34, 197, 94, 0.3);
  --el-button-text-color: #ffffff;
  --el-button-hover-bg-color: #16a34a;
  --el-button-hover-border-color: rgba(22, 163, 74, 0.34);
  --el-button-hover-text-color: #ffffff;
  --el-button-active-bg-color: #15803d;
  --el-button-active-border-color: rgba(21, 128, 61, 0.36);
  --el-button-active-text-color: #ffffff;
  --el-button-disabled-bg-color: #dcfce7;
  --el-button-disabled-border-color: #bbf7d0;
  --el-button-disabled-text-color: #6b7280;
  min-height: 44px;
  padding: 0 22px;
  border-radius: 14px;
  border: 1px solid rgba(34, 197, 94, 0.3);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
  color: #ffffff !important;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
  font-weight: 800;
}

.indicator-toolbar :deep(.el-button.indicator-toolbar__save:hover),
.indicator-toolbar :deep(.el-button.indicator-toolbar__save:focus-visible) {
  border-color: rgba(22, 163, 74, 0.34);
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
  color: #ffffff !important;
}

.indicator-list {
  display: grid;
  gap: 16px;
  margin-top: 18px;
}

.indicator-list__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
  padding: 18px 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.12), transparent 26%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: none;
}

.indicator-list__item.is-disabled {
  opacity: 0.72;
}

.indicator-list__main {
  min-width: 0;
  display: grid;
  gap: 10px;
}

.indicator-list__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.indicator-list__title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.indicator-list__code {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f5f0e7;
  color: #7e705c;
  font-size: 12px;
  font-weight: 700;
}

.indicator-list__desc {
  margin: 0;
  color: #5f6f85;
  font-size: 15px;
  line-height: 1.7;
}

.indicator-list__meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  align-self: center;
  gap: 10px;
  flex-wrap: wrap;
}

.indicator-list__pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #e5ddd1;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  color: #5f6f85;
  font-size: 13px;
  font-weight: 700;
}

.indicator-list__pill--source {
  background: #fff4e6;
  border-color: #ead7bc;
  color: #87633e;
}

.indicator-list__pill--weight {
  background: #fff9ec;
  border-color: #e5ddc8;
  color: #6f6a52;
}

.indicator-list__pill--active {
  border-color: #b9dd7f;
  background: #dff6b6;
  color: #2f5a37;
}

.indicator-list__pill--inactive {
  border-color: #e3ddd3;
  background: #f7f3ed;
  color: #877d70;
}

.indicator-weight-editor {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 6px;
  min-height: 32px;
}

.indicator-weight-editor__label {
  color: #7e705c;
  font-size: 13px;
  font-weight: 700;
}

.indicator-weight-editor :deep(.el-input-number) {
  width: 124px;
}

.indicator-weight-editor :deep(.el-input-number) {
  --el-input-number-controls-height: 40px;
}

.indicator-weight-editor :deep(.el-input-number__decrease),
.indicator-weight-editor :deep(.el-input-number__increase),
.indicator-weight-editor :deep(.el-input__wrapper) {
  min-height: 32px;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  border-color: #e5ddd1;
  color: #5e6b7d;
}

.indicator-weight-editor :deep(.el-input-number__decrease:hover),
.indicator-weight-editor :deep(.el-input-number__increase:hover) {
  color: #355a28;
  background: #eef5dd;
}

.indicator-weight-editor :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #e5ddd1 inset !important;
}

.indicator-weight-editor :deep(.el-input__inner) {
  color: #5e6b7d;
}

.indicator-list :deep(.el-checkbox__input.is-checked .el-checkbox__inner),
.indicator-list :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #9ac659;
  border-color: #9ac659;
}

.indicator-list :deep(.el-checkbox__inner:hover) {
  border-color: #9ac659;
}

.indicator-list :deep(.el-checkbox__input.is-checked + .el-checkbox__label),
.indicator-list :deep(.el-checkbox__label) {
  color: inherit;
}

.indicator-list :deep(.el-checkbox__input .el-checkbox__inner) {
  border-color: #cbbd9d;
  background: #ffffff;
}

.indicator-list :deep(.el-checkbox__input.is-disabled .el-checkbox__inner) {
  background: #f2f0eb;
  border-color: #d8d2c8;
}

@media (max-width: 1100px) {
  .indicator-master {
    grid-template-columns: 1fr;
  }

  .indicator-master__sidebar {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .indicator-list__item {
    grid-template-columns: 1fr;
  }

  .indicator-list__meta,
  .indicator-detail-header {
    justify-content: flex-start;
  }

  .indicator-detail-header {
    flex-direction: column;
  }

  .indicator-toolbar,
  .indicator-toolbar__controls {
    width: 100%;
    justify-items: start;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .indicator-toolbar__controls {
    flex-wrap: wrap;
  }

  .indicator-toolbar__select,
  .indicator-toolbar__select--course {
    width: 148px;
  }

  .indicator-weight-editor {
    width: 100%;
    justify-content: space-between;
    padding-left: 0;
  }
}
</style>
