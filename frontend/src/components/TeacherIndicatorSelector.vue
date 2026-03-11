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
    ElMessage.error(e?.response?.data?.detail ?? "加载课程画像指标失败");
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
          weight: Number(indicator.weight || indicator.default_weight || 1),
        }))
    );
    await api.put(`/portrait/course-selection?course_id=${props.courseId}`, { selections });
    ElMessage.success("课程画像指标已保存");
    await loadSelection();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存课程画像指标失败");
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
          <div class="indicator-header__kicker">Course Portrait Selection</div>
          <div class="indicator-header__title">课程画像指标选择</div>
          <div class="indicator-header__subtitle">
            管理员先配置一级维度和二级指标，教师再结合当前课程与可提供的数据选择要参与画像的指标。
          </div>
        </div>
        <div class="indicator-header__meta">
          <div class="indicator-metric">
            <span class="indicator-metric__label">当前课程</span>
            <strong>{{ subject || '未选择课程' }}</strong>
          </div>
          <div class="indicator-metric">
            <span class="indicator-metric__label">已启用指标</span>
            <strong>{{ enabledCount }}</strong>
          </div>
          <el-button type="primary" :loading="saving" @click="saveSelection">保存选择</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId" description="请先选择课程" :image-size="88" />
    <div v-else class="indicator-list">
      <el-card v-for="dimension in items" :key="dimension.id" class="indicator-card" shadow="never">
        <template #header>
          <div class="indicator-card__header">
            <div>
              <div class="indicator-card__code">{{ dimension.code }}</div>
              <div class="indicator-card__title">{{ dimension.title }}</div>
              <div class="indicator-card__desc">{{ dimension.description || '未填写说明' }}</div>
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
                <span>{{ indicator.source_type }}</span>
              </div>
              <div class="indicator-item__desc">{{ indicator.description || '暂无说明' }}</div>
            </div>
            <div class="indicator-item__side">
              <span class="indicator-item__weight-label">权重</span>
              <el-input-number v-model="indicator.weight" :min="0" :max="10" :step="0.1" size="small" />
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
