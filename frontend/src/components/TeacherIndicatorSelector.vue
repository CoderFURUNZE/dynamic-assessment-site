<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

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

const enabledCount = computed(() =>
  items.value.reduce((sum, dim) => sum + dim.indicators.filter((item) => item.enabled).length, 0)
);
const dimensionWeightSummary = computed(() =>
  items.value.map((dim) => {
    const enabledIndicators = dim.indicators.filter((indicator) => indicator.active && indicator.enabled);
    const total = enabledIndicators.reduce((sum, indicator) => sum + Number(indicator.weight || 0), 0);
    return {
      id: dim.id,
      title: dim.title,
      enabledCount: enabledIndicators.length,
      total,
    };
  })
);

function sourceTypeLabel(sourceType: string) {
  if (sourceType === "auto") return "系统自动";
  if (sourceType === "imported") return "阶段导入";
  if (sourceType === "teacher") return "老师填写";
  if (sourceType === "questionnaire") return "学生补充";
  return sourceType;
}

async function loadSelection() {
  if (!props.courseId) {
    items.value = [];
    return;
  }
  loading.value = true;
  try {
    const res = await api.get(`/portrait/course-selection?course_id=${props.courseId}`);
    items.value = (res.data?.items ?? []).map((dim: DimensionItem) => ({
      ...dim,
      indicators: (dim.indicators ?? []).map((indicator) => ({ ...indicator })),
    }));
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

watch(() => props.courseId, loadSelection, { immediate: true });
onMounted(loadSelection);
</script>

<template>
  <el-card class="panel-card indicator-shell" shadow="never" v-loading="loading">
    <template #header>
      <div class="indicator-header">
        <div>
          <div class="indicator-header__kicker">Course Indicator Setup</div>
          <div class="indicator-header__title">这门课看哪些内容</div>
          <div class="indicator-header__subtitle">
            先勾选这门课真正会用到的评价项。后面系统会按这些评价项生成学生学习情况。
          </div>
        </div>
        <div class="indicator-header__meta">
          <div class="indicator-metric">
            <span class="indicator-metric__label">当前课程</span>
            <strong>{{ subject || '未选择课程' }}</strong>
          </div>
          <div class="indicator-metric">
            <span class="indicator-metric__label">已选内容</span>
            <strong>{{ enabledCount }}</strong>
          </div>
          <div class="indicator-metric">
            <span class="indicator-metric__label">一级维度</span>
            <strong>{{ items.length }}</strong>
          </div>
          <el-button type="primary" :loading="saving" @click="saveSelection">保存设置</el-button>
        </div>
      </div>
    </template>

    <div v-if="!courseId" class="indicator-empty">
      <el-empty description="请先在页面顶部选择一门课程" :image-size="88" />
      <el-alert
        class="indicator-empty__tip"
        type="info"
        :closable="false"
        title="先选课程，再勾选这门课要看的内容。保存后，后面的阶段数据和学生学习情况才会按这些内容计算。"
      />
    </div>
    <div v-else class="indicator-list">
      <el-alert
        class="indicator-tip"
        type="info"
        :closable="false"
        title="只勾选这门课真正会用到的内容。系统拿得到数据的内容，后面才更容易算出结果。"
      />
      <el-card v-for="dimension in items" :key="dimension.id" class="indicator-card" shadow="never">
        <template #header>
          <div class="indicator-card__header">
            <div>
              <div class="indicator-card__code">{{ dimension.code }}</div>
              <div class="indicator-card__title">{{ dimension.title }}</div>
              <div class="indicator-card__desc">{{ dimension.description || '还没写说明' }}</div>
            </div>
            <div class="indicator-card__sum">
              总和 {{ (dimensionWeightSummary.find((item) => item.id === dimension.id)?.total ?? 0).toFixed(2) }}
            </div>
          </div>
        </template>

        <div class="indicator-grid">
          <div v-for="indicator in dimension.indicators" :key="indicator.id" class="indicator-item">
            <div class="indicator-item__main">
              <el-checkbox v-model="indicator.enabled" :disabled="!indicator.active">
                <span class="indicator-item__title">{{ indicator.title }}</span>
              </el-checkbox>
              <div class="indicator-item__meta">
                <span>{{ indicator.code }}</span>
                <span>{{ sourceTypeLabel(indicator.source_type) }}</span>
              </div>
              <div class="indicator-item__desc">{{ indicator.description || '还没写说明' }}</div>
            </div>
            <div class="indicator-item__side">
              <span class="indicator-item__weight-label">比重</span>
              <el-input-number v-model="indicator.weight" :min="0" :max="1" :step="0.05" size="small" />
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </el-card>
</template>

<style scoped>
.indicator-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.indicator-header__kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #6d8fc3;
  font-weight: 800;
}

.indicator-header__title {
  margin-top: 6px;
  font-size: 24px;
  font-weight: 800;
  color: #22395b;
}

.indicator-header__subtitle {
  margin-top: 8px;
  max-width: 760px;
  color: #6f809f;
  line-height: 1.7;
}

.indicator-header__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.indicator-metric {
  min-width: 120px;
  border: 1px solid rgba(109, 146, 211, 0.28);
  border-radius: 18px;
  padding: 12px 14px;
  background: rgba(244, 248, 255, 0.9);
}

.indicator-metric__label {
  display: block;
  color: #8090aa;
  font-size: 12px;
}

.indicator-list {
  display: grid;
  gap: 16px;
}

.indicator-empty {
  display: grid;
  gap: 14px;
}

.indicator-empty__tip {
  margin-top: -6px;
}

.indicator-tip {
  margin-bottom: 2px;
}

.indicator-card {
  border-radius: 24px;
}

.indicator-card__code {
  font-size: 12px;
  font-weight: 700;
  color: #6d8fc3;
}

.indicator-card__title {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 800;
  color: #22395b;
}

.indicator-card__desc {
  margin-top: 6px;
  color: #7283a1;
}

.indicator-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.indicator-card__sum {
  padding: 6px 12px;
  border-radius: 999px;
  background: #edf4ff;
  color: #355b97;
  font-size: 12px;
  font-weight: 700;
}

.indicator-grid {
  display: grid;
  gap: 12px;
}

.indicator-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  gap: 12px;
  border: 1px solid rgba(109, 146, 211, 0.24);
  border-radius: 18px;
  padding: 14px 16px;
  background: linear-gradient(180deg, rgba(247, 250, 255, 0.98), rgba(240, 246, 255, 0.98));
}

.indicator-item__title {
  font-weight: 700;
  color: #233b5c;
}

.indicator-item__meta,
.indicator-item__desc,
.indicator-item__weight-label {
  color: #7b8ba5;
  font-size: 13px;
}

.indicator-item__meta {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.indicator-item__desc {
  margin-top: 8px;
  line-height: 1.6;
}

.indicator-item__side {
  display: grid;
  align-content: center;
  justify-items: start;
  gap: 8px;
}

@media (max-width: 1100px) {
  .indicator-header,
  .indicator-item {
    grid-template-columns: 1fr;
    display: grid;
  }
}
</style>
