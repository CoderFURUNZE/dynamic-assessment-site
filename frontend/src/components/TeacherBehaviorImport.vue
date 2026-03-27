<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HintButton from "./HintButton.vue";

type BehaviorRow = {
  user_id: number;
  username: string;
  student_no: string;
  full_name: string;
  class_name: string;
  behavior_events: number;
  active_days: number;
  positive_events: number;
  negative_events: number;
  expression_events: number;
  expression_focus: number;
  expression_distracted: number;
  avg_confidence: number;
  behavior_score: number;
  signal_balance: number;
  dominant_signal: string;
  dynamic_score: number;
  risk_level: string;
};

type BehaviorSummary = {
  course_id: number;
  stage_id: number;
  stage_title: string;
  student_count: number;
  behavior_students: number;
  expression_students: number;
  positive_events: number;
  negative_events: number;
};

type BehaviorSummaryPayload = {
  summary: BehaviorSummary;
  rows: BehaviorRow[];
  columns: string[];
};

type ImportResult = {
  batch_id: number;
  metric_type: string;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  errors: string[];
  affected_dimensions: string[];
  affected_indicators: string[];
  recalculated_users: number;
  next_action: string;
};

const props = defineProps<{
  courseId: number | null;
  stageId: number | null;
  subject: string;
  grade: string;
  stageTitle: string;
}>();

const loading = ref(false);
const summary = ref<BehaviorSummaryPayload | null>(null);
const lastResult = ref<ImportResult | null>(null);

const previewRows = computed(() => summary.value?.rows.slice(0, 8) ?? []);

async function loadSummary() {
  if (!props.courseId || !props.stageId) {
    summary.value = null;
    return;
  }
  const res = await api.get(
    `/stages/internal-behavior-summary?course_id=${props.courseId}&stage_id=${props.stageId}`
  );
  summary.value = res.data ?? null;
}

async function refresh() {
  loading.value = true;
  try {
    await loadSummary();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载行为汇总失败");
  } finally {
    loading.value = false;
  }
}

async function downloadCsv() {
  if (!props.courseId || !props.stageId) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  try {
    const res = await api.get(
      `/stages/internal-behavior-summary/export?course_id=${props.courseId}&stage_id=${props.stageId}`,
      { responseType: "blob" }
    );
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `stage_behavior_summary_${props.courseId}_${props.stageId}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导出行为汇总失败");
  }
}

async function applyBehavior() {
  if (!props.courseId || !props.stageId) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  try {
    const form = new FormData();
    form.append("course_id", String(props.courseId));
    form.append("stage_id", String(props.stageId));
    const res = await api.post("/stages/internal-behavior-summary/apply", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    lastResult.value = res.data ?? null;
    ElMessage.success("行为信息已导入并生成阶段画像");
    await loadSummary();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "应用行为汇总失败");
  }
}

watch(
  () => [props.courseId, props.stageId],
  () => {
    refresh();
  },
  { immediate: true }
);
</script>

<template>
  <el-card class="behavior-card" shadow="never" v-loading="loading">
    <template #header>
      <div class="behavior-header">
        <div class="behavior-header__main">
          <div class="behavior-header__eyebrow">Behavior Import</div>
          <div class="behavior-title">系统行为汇总</div>
          <div class="behavior-subtitle">
            汇总系统自动采集的资源访问、图谱浏览、作答和表情/行为信号，生成阶段画像输入。
          </div>
        </div>
        <div class="behavior-actions">
          <HintButton size="small" tip="重新加载当前阶段的行为汇总。" @click="refresh">刷新</HintButton>
          <HintButton size="small" tip="导出当前阶段的行为汇总 CSV。" @click="downloadCsv">导出 CSV</HintButton>
          <HintButton size="small" type="primary" tip="把当前行为汇总写入阶段画像并重算学生画像。" @click="applyBehavior">一键导入行为并生成画像</HintButton>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId || !stageId" description="请先选择课程和阶段" />

    <template v-else>
      <div class="behavior-banner" v-if="summary">
        <div class="behavior-banner__title">当前阶段行为画像输入</div>
        <div class="behavior-banner__meta">
          系统会把行为事件按学生与日期汇总，导入后直接生成阶段画像，便于老师核对。
        </div>
      </div>

      <div class="behavior-overview" v-if="summary">
        <div class="behavior-overview__card">
          <span>当前课程</span>
          <strong>{{ subject || "未选择课程" }}</strong>
          <small>{{ grade || "通用" }} · {{ stageTitle || "未选择阶段" }}</small>
        </div>
        <div class="behavior-overview__card">
          <span>行为学生</span>
          <strong>{{ summary.summary.behavior_students }}</strong>
          <small>发生过系统行为事件的学生数</small>
        </div>
        <div class="behavior-overview__card">
          <span>表情学生</span>
          <strong>{{ summary.summary.expression_students }}</strong>
          <small>采集到表情/行为信号的学生数</small>
        </div>
        <div class="behavior-overview__card">
          <span>正向 / 负向</span>
          <strong>{{ summary.summary.positive_events }} / {{ summary.summary.negative_events }}</strong>
          <small>正向事件与分心/负向事件总量</small>
        </div>
      </div>

      <div class="behavior-table" v-if="summary">
        <div class="behavior-table__title">行为预览</div>
        <div class="behavior-table__surface">
          <el-table :data="previewRows" size="small" style="width: 100%">
          <el-table-column prop="username" label="账号" width="120" />
          <el-table-column prop="student_no" label="学号" width="120" />
          <el-table-column prop="behavior_events" label="事件数" width="90" />
          <el-table-column prop="active_days" label="活跃天数" width="100" />
          <el-table-column prop="expression_events" label="表情数" width="90" />
          <el-table-column prop="behavior_score" label="行为得分" width="110">
            <template #default="{ row }">{{ Math.round((row.behavior_score || 0) * 100) }}%</template>
          </el-table-column>
          <el-table-column prop="dynamic_score" label="当前画像" width="110">
            <template #default="{ row }">{{ Math.round((row.dynamic_score || 0) * 100) }}%</template>
          </el-table-column>
          <el-table-column prop="dominant_signal" label="主信号" min-width="120" />
          <el-table-column prop="risk_level" label="风险" width="100" />
          </el-table>
        </div>
      </div>

      <div v-if="lastResult" class="behavior-result">
        <div class="behavior-result__item">
          <span>导入记录</span>
          <strong>{{ lastResult.total_rows }}</strong>
        </div>
        <div class="behavior-result__item">
          <span>成功导入</span>
          <strong>{{ lastResult.success_rows }}</strong>
        </div>
        <div class="behavior-result__item">
          <span>重算学生</span>
          <strong>{{ lastResult.recalculated_users }}</strong>
        </div>
        <div class="behavior-result__item behavior-result__item--full">
          <span>下一步</span>
          <strong>{{ lastResult.next_action }}</strong>
        </div>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.behavior-card {
  margin-top: 16px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background:
    radial-gradient(circle at top right, rgba(79, 140, 255, 0.08), transparent 32%),
    linear-gradient(180deg, rgba(10, 17, 28, 0.98), rgba(12, 20, 34, 0.995));
  box-shadow: 0 20px 50px rgba(2, 8, 20, 0.2);
}

.behavior-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.behavior-header__main {
  display: grid;
  gap: 6px;
}

.behavior-header__eyebrow {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.82);
}

.behavior-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--app-ink, #e8eef8);
  letter-spacing: -0.02em;
}

.behavior-subtitle {
  color: rgba(226, 232, 240, 0.7);
  font-size: 13px;
  line-height: 1.7;
  max-width: 760px;
}

.behavior-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.behavior-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.55);
}

.behavior-banner__title {
  font-size: 13px;
  font-weight: 700;
  color: #f8fafc;
}

.behavior-banner__meta {
  color: rgba(226, 232, 240, 0.68);
  font-size: 12px;
  line-height: 1.6;
}

.behavior-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.behavior-overview__card {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.015)),
    rgba(15, 23, 42, 0.82);
  display: grid;
  gap: 6px;
}

.behavior-overview__card span,
.behavior-result__item span {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.6);
}

.behavior-overview__card strong,
.behavior-result__item strong {
  font-size: 20px;
  color: #f8fafc;
  line-height: 1.3;
}

.behavior-overview__card small {
  color: rgba(226, 232, 240, 0.55);
  font-size: 12px;
}

.behavior-table {
  margin-bottom: 16px;
}

.behavior-table__title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #e5eef9;
}

.behavior-table__surface {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.7);
}

.behavior-result {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 0 4px;
}

.behavior-result__item {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 4px;
}

.behavior-result__item--full {
  grid-column: 1 / -1;
}

@media (max-width: 1100px) {
  .behavior-overview,
  .behavior-result {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .behavior-header {
    gap: 12px;
  }

  .behavior-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .behavior-overview,
  .behavior-result {
    grid-template-columns: 1fr;
  }
}
</style>
