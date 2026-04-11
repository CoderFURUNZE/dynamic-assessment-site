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
}>();

const loading = ref(false);
const saving = ref(false);
const items = ref<DimensionItem[]>([]);
const selectedDimensionId = ref<number | null>(null);

const enabledCount = computed(() =>
  items.value.reduce((sum, dim) => sum + dim.indicators.filter((item) => item.enabled).length, 0)
);

const selectedDimension = computed(
  () => items.value.find((item) => item.id === selectedDimensionId.value) ?? items.value[0] ?? null
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
  if (sourceType === "teacher") return "老师补充";
  if (sourceType === "questionnaire") return "学生补充";
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
        }))
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
    loadSelection();
  },
  { immediate: true }
);

watch(
  items,
  () => {
    ensureSelectedDimension();
  },
  { deep: true }
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
            <div>
              <div class="indicator-detail-header__title">评价维度大类与细类</div>
              <div class="indicator-detail-header__meta">
                {{ selectedDimension ? `${selectedDimension.title}，默认展示该大类下的细项` : "先从左侧选择一个一级维度" }}
              </div>
            </div>
          </div>

          <el-empty
            v-if="!selectedDimension"
            description="当前没有可配置的一级维度"
            :image-size="72"
          />

          <div v-else class="indicator-list">
            <article
              v-for="indicator in selectedDimension.indicators"
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
                <p class="indicator-list__desc">{{ indicator.description || "还没写说明" }}</p>
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
  border: 1px solid #d7e4f5;
  border-radius: 28px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 14px 30px rgba(109, 146, 211, 0.1);
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
  border: 1px solid #dbe5f1;
  border-radius: 20px;
  background: #ffffff;
  padding: 18px 18px;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.dimension-card:hover {
  border-color: #aac6f7;
  box-shadow: 0 10px 20px rgba(93, 131, 192, 0.08);
}

.dimension-card.is-active {
  border-color: #c8dfbc;
  background: linear-gradient(180deg, #f4fbef 0%, #eef8e7 100%);
  box-shadow: 0 12px 24px rgba(116, 154, 92, 0.12);
}

.dimension-card__title {
  font-size: 15px;
  font-weight: 800;
  color: #22395b;
  line-height: 1.5;
}

.indicator-master__detail {
  min-width: 0;
}

.indicator-detail-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 2px 0 16px;
  border-bottom: 1px solid #dbe5f1;
}

.indicator-detail-header__title {
  font-size: 18px;
  font-weight: 800;
  color: #1f3960;
}

.indicator-detail-header__meta {
  margin-top: 6px;
  font-size: 12px;
  color: #6f809f;
}

.summary-pill {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #d7e4f5;
  background: #f7faff;
  color: #355b97;
  font-size: 13px;
  font-weight: 700;
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
  border: 1px solid #dbe5f1;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
  box-shadow: 0 10px 24px rgba(87, 116, 166, 0.08);
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
  color: #22395b;
}

.indicator-list__code {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f3f7ff;
  color: #6f809f;
  font-size: 12px;
  font-weight: 700;
}

.indicator-list__desc {
  margin: 0;
  color: #5f7188;
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
  border: 1px solid #d7e4f5;
  background: #ffffff;
  color: #4d617d;
  font-size: 13px;
  font-weight: 700;
}

.indicator-list__pill--source {
  background: #f6f9ff;
  color: #46638c;
}

.indicator-list__pill--weight {
  background: #f9fbff;
  color: #3b6487;
}

.indicator-list__pill--active {
  border-color: #c8dfbc;
  background: #f0f9eb;
  color: #48643d;
}

.indicator-list__pill--inactive {
  border-color: #e4e9f1;
  background: #f7f9fc;
  color: #7a889f;
}

.indicator-weight-editor {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 6px;
  min-height: 32px;
}

.indicator-weight-editor__label {
  color: #7b8ba5;
  font-size: 13px;
  font-weight: 700;
}

.indicator-weight-editor :deep(.el-input-number) {
  width: 124px;
}

.indicator-weight-editor :deep(.el-input-number__decrease),
.indicator-weight-editor :deep(.el-input-number__increase),
.indicator-weight-editor :deep(.el-input__wrapper) {
  min-height: 32px;
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
}

@media (max-width: 720px) {
  .indicator-toolbar {
    justify-content: flex-start;
  }

  .indicator-toolbar__meta {
    width: 100%;
  }

  .indicator-metric {
    min-width: calc(50% - 6px);
  }

  .indicator-weight-editor {
    width: 100%;
    justify-content: space-between;
    padding-left: 0;
  }
}
</style>
