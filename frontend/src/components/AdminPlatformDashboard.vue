<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type ChartRow = {
  label: string;
  value: number;
  hint: string;
  color: string;
};

const loading = ref(false);
const stats = reactive({
  totalUsers: 0,
  totalTeachers: 0,
  totalStudents: 0,
  totalAdmins: 0,
  totalDimensions: 0,
  totalIndicators: 0,
});

const userScaleRows = computed<ChartRow[]>(() => [
  { label: "用户总数", value: stats.totalUsers, hint: "全部账号", color: "#2ea7a0" },
  { label: "教师数量", value: stats.totalTeachers, hint: "教师", color: "#ffd67a" },
  { label: "学生数量", value: stats.totalStudents, hint: "学生", color: "#ff9b45" },
  { label: "管理员数量", value: stats.totalAdmins, hint: "管理员", color: "#344283" },
]);

const evaluationRows = computed<ChartRow[]>(() => [
  { label: "一级指标数", value: stats.totalDimensions, hint: "维度", color: "#52a7ff" },
  { label: "二级指标数", value: stats.totalIndicators, hint: "细项", color: "#2cb67d" },
]);

function buildTicks(maxValue: number) {
  const ceiling = Math.max(maxValue, 1);
  const roughStep = Math.ceil(ceiling / 4);
  const magnitude = 10 ** Math.max(String(roughStep).length - 1, 0);
  const step = Math.max(Math.ceil(roughStep / magnitude) * magnitude, 1);
  return Array.from({ length: 5 }, (_, index) => step * (4 - index));
}

const userMax = computed(() => Math.max(...userScaleRows.value.map((item) => item.value), 1));
const evaluationMax = computed(() => Math.max(...evaluationRows.value.map((item) => item.value), 1));
const userTicks = computed(() => buildTicks(userMax.value));
const evaluationTicks = computed(() => buildTicks(evaluationMax.value));

function barHeight(value: number, maxValue: number) {
  if (maxValue <= 0) {
    return "10%";
  }
  return `${Math.max((value / maxValue) * 100, 8)}%`;
}

async function load() {
  loading.value = true;
  try {
    const [usersAll, teachers, students, admins, dimensions] = await Promise.all([
      api.get("/admin/users?page=1&page_size=1"),
      api.get("/admin/users?page=1&page_size=1&role=teacher"),
      api.get("/admin/users?page=1&page_size=1&role=student"),
      api.get("/admin/users?page=1&page_size=1&role=admin"),
      api.get("/portrait/dimensions/tree"),
    ]);

    stats.totalUsers = Number(usersAll.data?.total ?? 0);
    stats.totalTeachers = Number(teachers.data?.total ?? 0);
    stats.totalStudents = Number(students.data?.total ?? 0);
    stats.totalAdmins = Number(admins.data?.total ?? 0);

    const dimensionsTree = dimensions.data?.items ?? [];
    stats.totalDimensions = dimensionsTree.length;
    stats.totalIndicators = dimensionsTree.reduce(
      (sum: number, item: any) => sum + Number(item?.indicators?.length ?? 0),
      0,
    );
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载平台数据概览失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="dashboard-shell" v-loading="loading">
    <section class="edu-panel dashboard-chart-panel">
      <header class="edu-panel__header">
        <h2 class="edu-panel__title">平台数据概览</h2>
      </header>

      <div class="dashboard-chart-grid">
        <article class="chart-card">
          <div class="chart-card__head">
            <strong>用户规模</strong>
            <span>账号结构</span>
          </div>
          <div class="bar-chart">
            <div class="bar-chart__axis">
              <span v-for="tick in userTicks" :key="tick">{{ tick }}</span>
              <span>0</span>
            </div>
            <div class="bar-chart__plot">
              <div v-for="tick in userTicks" :key="`user-grid-${tick}`" class="bar-chart__grid-line" />
              <div class="bar-chart__baseline" />
              <div class="bar-chart__bars">
                <div v-for="item in userScaleRows" :key="item.label" class="bar-chart__item">
                  <div class="bar-chart__value">{{ item.value }}</div>
                  <div class="bar-chart__column-wrap">
                    <div class="bar-chart__bar" :style="{ height: barHeight(item.value, userMax), background: item.color }" />
                  </div>
                  <div class="bar-chart__label">{{ item.label }}</div>
                  <div class="bar-chart__hint">{{ item.hint }}</div>
                </div>
              </div>
            </div>
          </div>
        </article>

        <article class="chart-card">
          <div class="chart-card__head">
            <strong>评价配置</strong>
            <span>指标结构</span>
          </div>
          <div class="bar-chart">
            <div class="bar-chart__axis">
              <span v-for="tick in evaluationTicks" :key="tick">{{ tick }}</span>
              <span>0</span>
            </div>
            <div class="bar-chart__plot">
              <div v-for="tick in evaluationTicks" :key="`eval-grid-${tick}`" class="bar-chart__grid-line" />
              <div class="bar-chart__baseline" />
              <div class="bar-chart__bars bar-chart__bars--wide">
                <div v-for="item in evaluationRows" :key="item.label" class="bar-chart__item">
                  <div class="bar-chart__value">{{ item.value }}</div>
                  <div class="bar-chart__column-wrap">
                    <div class="bar-chart__bar" :style="{ height: barHeight(item.value, evaluationMax), background: item.color }" />
                  </div>
                  <div class="bar-chart__label">{{ item.label }}</div>
                  <div class="bar-chart__hint">{{ item.hint }}</div>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard-shell {
  display: grid;
  gap: 24px;
}

.dashboard-chart-panel {
  padding: 0;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  overflow: visible;
}

.dashboard-chart-panel::before {
  display: none;
}

.dashboard-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 10px;
}

.chart-card {
  padding: 24px;
  border-radius: 30px;
  border: 3px solid #1f2937;
  background: radial-gradient(circle at top right, rgba(210, 238, 255, 0.72), transparent 42%), #fffdf6;
  display: grid;
  gap: 14px;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.chart-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.chart-card__head strong {
  font-size: 20px;
  color: var(--app-text-main);
}

.chart-card__head span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.bar-chart {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 12px;
  min-height: 320px;
}

.bar-chart__axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  padding: 18px 0 26px;
  font-size: 12px;
  color: var(--app-text-soft);
}

.bar-chart__plot {
  position: relative;
  min-height: 320px;
  padding: 14px 8px 0;
}

.bar-chart__grid-line,
.bar-chart__baseline {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 2px dashed rgba(71, 85, 105, 0.24);
}

.bar-chart__grid-line:nth-of-type(1) { top: 18px; }
.bar-chart__grid-line:nth-of-type(2) { top: 25%; }
.bar-chart__grid-line:nth-of-type(3) { top: 50%; }
.bar-chart__grid-line:nth-of-type(4) { top: 75%; }

.bar-chart__baseline {
  top: auto;
  bottom: 54px;
  border-top-style: solid;
  border-top-width: 2px;
  border-top-color: rgba(6, 78, 59, 0.45);
}

.bar-chart__bars {
  position: absolute;
  left: 18px;
  right: 18px;
  top: 10px;
  bottom: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  align-items: end;
}

.bar-chart__bars--wide {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 36px;
}

.bar-chart__item {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.bar-chart__value {
  font-size: 18px;
  font-weight: 800;
  color: var(--app-text-main);
  line-height: 1;
}

.bar-chart__column-wrap {
  height: 210px;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.bar-chart__bar {
  width: min(48px, 78%);
  min-height: 20px;
  border-radius: 14px 14px 6px 6px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.1);
}

.bar-chart__label {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-text-main);
  text-align: center;
}

.bar-chart__hint {
  font-size: 12px;
  color: var(--app-text-soft);
  text-align: center;
}

@media (max-width: 960px) {
  .dashboard-chart-grid {
    grid-template-columns: 1fr;
  }

  .bar-chart {
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .bar-chart__bars {
    gap: 12px;
  }
}
</style>
