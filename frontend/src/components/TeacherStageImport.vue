<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";
import HintButton from "./HintButton.vue";
import TeacherBehaviorImport from "./TeacherBehaviorImport.vue";

type Stage = {
  id: number;
  title: string;
  stage_order: number;
};

type ImportBatch = {
  id: number;
  course_id: number;
  stage_id: number;
  stage_title: string;
  subject: string;
  grade: string;
  metric_type: string;
  file_name: string;
  uploaded_by: string;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  error_preview: string[];
  created_at: string;
};

type MetricGuide = {
  metric_type: string;
  label: string;
  summary: string;
  template_fields: string[];
  affected_dimensions: string[];
  affected_indicators: string[];
  next_action: string;
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

type InternalSummaryRow = {
  user_id: number;
  username: string;
  student_no: string;
  full_name: string;
  class_name: string;
  watched_minutes: number;
  avg_video_completion: number;
  practice_attempts: number;
  practice_accuracy: number;
  recommendation_count: number;
  questionnaire_updates: number;
  course_mastery: number;
  dynamic_score: number;
  risk_level: string;
};

type InternalSummary = {
  summary: {
    course_id: number;
    stage_id: number;
    stage_title: string;
    student_count: number;
    video_students: number;
    practice_students: number;
    questionnaire_students: number;
    recommendation_students: number;
  };
  rows: InternalSummaryRow[];
  columns: string[];
};

const props = defineProps<{
  courseId: number | null;
  subject: string;
  grade: string;
}>();
const emit = defineEmits<{
  (e: "view-profiles"): void;
}>();

const loading = ref(false);
const stages = ref<Stage[]>([]);
const batches = ref<ImportBatch[]>([]);
const metricGuides = ref<MetricGuide[]>([]);
const selectedStageId = ref<number | null>(null);
const metricType = ref("video");
const uploadFile = ref<File | null>(null);
const lastResult = ref<ImportResult | null>(null);
const internalSummary = ref<InternalSummary | null>(null);
const systemMappings = reactive({
  video: true,
  practice: true,
  mastery: true,
});

const metricOptions = [
  { label: "视频学习记录", value: "video" },
  { label: "作业完成记录", value: "assignment" },
  { label: "考勤记录", value: "attendance" },
  { label: "任务完成记录", value: "task" },
  { label: "课堂参与记录", value: "participation" },
];

const canUpload = computed(() => Boolean(props.courseId && selectedStageId.value && uploadFile.value));
const selectedGuide = computed(() => metricGuides.value.find((item) => item.metric_type === metricType.value) ?? null);
const enabledSystemMappings = computed(
  () => [systemMappings.video, systemMappings.practice, systemMappings.mastery].filter(Boolean).length
);

async function loadGuides() {
  const res = await api.get("/stages/metric-guides");
  metricGuides.value = res.data ?? [];
}

async function loadStages() {
  if (!props.courseId) {
    stages.value = [];
    selectedStageId.value = null;
    return;
  }
  const res = await api.get(`/stages/courses/${props.courseId}`);
  stages.value = res.data ?? [];
  const exists = stages.value.some((item) => item.id === selectedStageId.value);
  if (!exists) {
    selectedStageId.value = stages.value.length ? stages.value[0].id : null;
  }
}

async function loadBatches() {
  if (!props.courseId) {
    batches.value = [];
    return;
  }
  const query = new URLSearchParams({ course_id: String(props.courseId) });
  if (selectedStageId.value) query.set("stage_id", String(selectedStageId.value));
  const res = await api.get(`/stages/imports?${query.toString()}`);
  batches.value = res.data ?? [];
}

async function loadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) {
    internalSummary.value = null;
    return;
  }
  const res = await api.get(`/stages/internal-summary?course_id=${props.courseId}&stage_id=${selectedStageId.value}`);
  internalSummary.value = res.data ?? null;
}

async function refresh() {
  loading.value = true;
  try {
    await loadGuides();
    if (!props.courseId) {
      stages.value = [];
      batches.value = [];
      internalSummary.value = null;
      return;
    }
    await loadStages();
    await loadBatches();
    await loadInternalSummary();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载导入数据失败");
  } finally {
    loading.value = false;
  }
}

function handleExternalStageChange(event: Event) {
  const custom = event as CustomEvent<{ courseId?: number | null }>;
  const changedCourseId = Number(custom.detail?.courseId || 0);
  if (!props.courseId) return;
  if (!changedCourseId || changedCourseId === Number(props.courseId)) {
    refresh().catch((e: any) => {
      ElMessage.error(e?.response?.data?.detail ?? "同步阶段数据失败");
    });
  }
}

function onFileChange(file: any) {
  uploadFile.value = file?.raw ?? null;
}

async function upload() {
  if (!canUpload.value || !props.courseId || !selectedStageId.value || !uploadFile.value) {
    ElMessage.warning("请选择阶段和导入文件");
    return;
  }
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("metric_type", metricType.value);
  form.append("file", uploadFile.value);
  try {
    const res = await api.post("/stages/imports/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const data = res.data;
    lastResult.value = data;
    ElMessage.success(
      `导入完成：成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条，已重算 ${data.recalculated_users ?? 0} 名学生`
    );
    uploadFile.value = null;
    await loadBatches();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导入失败");
  }
}

function openProfiles() {
  emit("view-profiles");
}

async function downloadTemplate() {
  try {
    const res = await api.get(`/stages/template?metric_type=${encodeURIComponent(metricType.value)}`, {
      responseType: "blob",
    });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `stage_template_${metricType.value}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "下载模板失败");
  }
}

async function downloadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  try {
    const res = await api.get(`/stages/internal-summary/export?course_id=${props.courseId}&stage_id=${selectedStageId.value}`, {
      responseType: "blob",
    });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `internal_stage_summary_${props.courseId}_${selectedStageId.value}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "下载系统汇总失败");
  }
}

async function applyInternalSummary() {
  if (!props.courseId || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  if (!enabledSystemMappings.value) {
    ElMessage.warning("请至少选择一个系统汇总映射项");
    return;
  }
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("include_video", String(systemMappings.video));
  form.append("include_practice", String(systemMappings.practice));
  form.append("include_mastery", String(systemMappings.mastery));
  try {
    const res = await api.post("/stages/internal-summary/apply", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const data = res.data;
    lastResult.value = data;
    ElMessage.success(
      `系统数据已应用：生成 ${data.success_rows} 条阶段记录，已重算 ${data.recalculated_users ?? 0} 名学生画像`
    );
    await loadBatches();
    await loadInternalSummary();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "应用系统汇总失败");
  }
}

watch(
  () => props.courseId,
  () => {
    uploadFile.value = null;
    refresh();
  },
  { immediate: true }
);

watch(selectedStageId, () => {
  loadBatches().catch((e: any) => {
    ElMessage.error(e?.response?.data?.detail ?? "加载导入历史失败");
  });
  loadInternalSummary().catch((e: any) => {
    ElMessage.error(e?.response?.data?.detail ?? "加载系统汇总失败");
  });
});

onMounted(() => {
  window.addEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener);
});

onBeforeUnmount(() => {
  window.removeEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener);
});
</script>

<template>
  <el-card class="panel-card" shadow="never" v-loading="loading">
    <template #header>
      <div class="import-header">
        <div>
          <div class="import-title">阶段数据导入</div>
          <div class="import-subtitle">按阶段上传视频、作业、考勤或任务数据，作为后续画像与动态评价的输入来源。</div>
        </div>
        <div class="import-actions">
          <HintButton size="small" tip="刷新导入历史、模板和系统汇总。" @click="refresh" :loading="loading">刷新</HintButton>
          <HintButton size="small" tip="下载当前数据类型对应的导入模板。" @click="downloadTemplate">下载模板</HintButton>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId" description="请先在顶部选择课程" />

    <template v-else>
      <div class="import-overview">
        <div class="import-overview__card">
          <span>当前课程</span>
          <strong>{{ subject || "未选择课程" }}</strong>
          <small>先选阶段，再导入整班阶段数据</small>
        </div>
        <div class="import-overview__card">
          <span>当前阶段</span>
          <strong>{{ stages.find((item) => item.id === selectedStageId)?.title || "未选择阶段" }}</strong>
          <small>一份表可包含全班学生记录</small>
        </div>
        <div class="import-overview__card">
          <span>最近重算人数</span>
          <strong>{{ lastResult?.recalculated_users ?? 0 }}</strong>
          <small>最近一次导入后生成画像的学生数</small>
        </div>
      </div>

      <div class="import-grid">
        <section class="import-panel">
          <div class="import-auto-card">
            <div class="panel-mini-title">系统自动汇总</div>
          <div class="import-auto-card__text">
            系统会先按当前课程和阶段，自动汇总平台内已有的学习数据：视频学习、练习、推荐推进、问卷更新和当前掌握度。
          </div>
          <div class="mapping-panel">
            <div class="mapping-panel__title">系统汇总映射配置</div>
            <div class="mapping-list">
              <label class="mapping-item">
                <el-switch v-model="systemMappings.video" />
                <div class="mapping-item__body">
                  <strong>视频学习数据</strong>
                  <span>映射为“视频学习记录”，写入观看分钟数和平均完成率。</span>
                </div>
              </label>
              <label class="mapping-item">
                <el-switch v-model="systemMappings.practice" />
                <div class="mapping-item__body">
                  <strong>练习表现数据</strong>
                  <span>映射为“作业完成记录”，写入练习次数、正确率和完成度。</span>
                </div>
              </label>
              <label class="mapping-item">
                <el-switch v-model="systemMappings.mastery" />
                <div class="mapping-item__body">
                  <strong>掌握与推进数据</strong>
                  <span>映射为“任务完成记录”，写入掌握度、推荐推进和问卷补充情况。</span>
                </div>
              </label>
            </div>
            <div class="mapping-panel__hint">
              当前会生成 {{ enabledSystemMappings }} 类阶段记录。后续外部补充导入会叠加到同一阶段，再次重算学生画像。
            </div>
          </div>
          <div class="import-auto-card__actions">
            <HintButton tip="重新加载系统自动采集到的阶段数据。" @click="loadInternalSummary">刷新系统数据</HintButton>
            <HintButton tip="导出系统采集到的阶段行为汇总 CSV。" @click="downloadInternalSummary">导出系统汇总 CSV</HintButton>
            <HintButton type="primary" tip="把系统汇总写入阶段画像并重算学生画像。" @click="applyInternalSummary">一键应用并生成画像</HintButton>
          </div>
            <div v-if="internalSummary" class="import-auto-card__stats">
              <div class="import-auto-card__stat">
                <span>学生总数</span>
                <strong>{{ internalSummary.summary.student_count }}</strong>
              </div>
              <div class="import-auto-card__stat">
                <span>有视频数据</span>
                <strong>{{ internalSummary.summary.video_students }}</strong>
              </div>
              <div class="import-auto-card__stat">
                <span>有练习数据</span>
                <strong>{{ internalSummary.summary.practice_students }}</strong>
              </div>
              <div class="import-auto-card__stat">
                <span>有推荐推进</span>
                <strong>{{ internalSummary.summary.recommendation_students }}</strong>
              </div>
            </div>
          </div>

          <div class="panel-mini-title">全班阶段数据导入</div>
          <div class="import-tip-inline">
            <span>导入说明</span>
            <HoverTip content="按顺序做：先选阶段，再选数据类型，再下载模板，最后上传全班 CSV / XLSX。导入成功后系统会批量重算该阶段学生画像。" />
          </div>
          <el-form label-width="110px">
            <el-form-item label="课程">
              <el-input :model-value="subject || '未选择课程'" disabled />
            </el-form-item>
            <el-form-item>
              <template #label>
                <el-tooltip content="这批数据属于哪个学习阶段，就选哪个阶段。" :show-after="700">
                  <span>阶段</span>
                </el-tooltip>
              </template>
              <el-select v-model="selectedStageId" style="width: 100%" placeholder="选择阶段">
                <el-option v-for="item in stages" :key="item.id" :label="`${item.stage_order}. ${item.title}`" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <template #label>
                <el-tooltip content="视频、作业、考勤等要分开导入，避免字段混乱。" :show-after="700">
                  <span>数据类型</span>
                </el-tooltip>
              </template>
              <el-select v-model="metricType" style="width: 100%">
                <el-option v-for="item in metricOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="上传文件">
              <el-upload :auto-upload="false" :show-file-list="true" :limit="1" @change="onFileChange">
                <el-button>选择全班 CSV / XLSX</el-button>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <HintButton type="primary" :disabled="!canUpload" tip="上传整班文件，并按当前阶段批量生成画像。" @click="upload">一键导入并生成画像</HintButton>
            </el-form-item>
          </el-form>
          <div class="import-hint">
            当前支持按模板一次导入整班阶段数据。建议先下载模板，再按示例字段填充，至少保证 `username` 或 `student_no` 能匹配到学生。
          </div>
          <div class="import-hint import-hint--merge">
            系统自动汇总生成的阶段记录，与老师后续上传的线下考勤、课堂参与、口头展示等补充数据，会共同保留在当前阶段并再次触发重算。
          </div>
          <TeacherBehaviorImport
            :course-id="courseId"
            :stage-id="selectedStageId"
            :subject="subject"
            :grade="grade"
            :stage-title="stages.find((item) => item.id === selectedStageId)?.title || ''"
          />
        </section>

        <section class="import-panel import-panel--history">
          <div v-if="internalSummary" class="guide-panel">
            <div class="panel-mini-title">系统内阶段数据预览</div>
            <div class="guide-summary">
              这部分是系统已经自动采集到的数据，可直接导出给老师核对；线下考勤、课堂参与、口头展示等仍建议老师补充导入。
            </div>
            <el-table :data="internalSummary.rows.slice(0, 8)" size="small" style="width: 100%">
              <el-table-column prop="username" label="账号" width="120" />
              <el-table-column prop="student_no" label="学号" width="120" />
              <el-table-column prop="watched_minutes" label="视频分钟" width="110" />
              <el-table-column label="练习正确率" width="120">
                <template #default="{ row }">{{ Math.round((row.practice_accuracy || 0) * 100) }}%</template>
              </el-table-column>
              <el-table-column prop="practice_attempts" label="练习次数" width="100" />
              <el-table-column label="掌握度" width="100">
                <template #default="{ row }">{{ Math.round((row.course_mastery || 0) * 100) }}%</template>
              </el-table-column>
              <el-table-column label="动态评分" width="100">
                <template #default="{ row }">{{ Math.round((row.dynamic_score || 0) * 100) }}%</template>
              </el-table-column>
              <el-table-column prop="risk_level" label="风险等级" min-width="120" />
            </el-table>
          </div>

          <div v-if="lastResult" class="import-result-card">
            <div class="panel-mini-title">最近一次批量生成结果</div>
            <div class="import-result-card__metrics">
              <div class="import-result-card__metric">
                <span>总记录</span>
                <strong>{{ lastResult.total_rows }}</strong>
              </div>
              <div class="import-result-card__metric">
                <span>成功导入</span>
                <strong>{{ lastResult.success_rows }}</strong>
              </div>
              <div class="import-result-card__metric">
                <span>失败记录</span>
                <strong>{{ lastResult.failed_rows }}</strong>
              </div>
              <div class="import-result-card__metric">
                <span>生成画像学生</span>
                <strong>{{ lastResult.recalculated_users }}</strong>
              </div>
            </div>
            <div class="import-result-card__next">
              {{ lastResult.next_action || "导入完成后，可直接进入学生画像页查看这次阶段重算结果。" }}
            </div>
            <div class="import-result-card__actions">
              <HintButton type="primary" tip="跳转到学生画像页查看本次导入结果。" @click="openProfiles">查看学生画像</HintButton>
            </div>
            <div v-if="lastResult.errors?.length" class="error-stack">
              <div v-for="item in lastResult.errors.slice(0, 5)" :key="item">{{ item }}</div>
            </div>
          </div>

          <div v-if="selectedGuide" class="guide-panel">
            <div class="panel-mini-title">当前数据类型说明</div>
            <div class="guide-summary">{{ selectedGuide.summary }}</div>
            <div class="guide-block">
              <div class="guide-label">模板字段</div>
              <div class="guide-chips">
                <span v-for="item in selectedGuide.template_fields" :key="item" class="guide-chip">
                  {{ item }}
                </span>
              </div>
            </div>
            <div class="guide-block">
              <div class="guide-label">影响的一级维度</div>
              <div class="guide-chips">
                <span v-for="item in selectedGuide.affected_dimensions" :key="item" class="guide-chip guide-chip--blue">
                  {{ item }}
                </span>
              </div>
            </div>
            <div class="guide-block">
              <div class="guide-label">主要影响的二级指标</div>
              <div class="guide-chips">
                <span v-for="item in selectedGuide.affected_indicators" :key="item" class="guide-chip guide-chip--soft">
                  {{ item }}
                </span>
              </div>
            </div>
            <div class="guide-next">
              {{ selectedGuide.next_action }}
            </div>
          </div>
          <div class="panel-mini-title">导入历史</div>
          <el-table :data="batches" size="small" style="width: 100%">
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">{{ row.created_at.replace('T', ' ').slice(0, 19) }}</template>
            </el-table-column>
            <el-table-column prop="stage_title" label="阶段" min-width="180" />
            <el-table-column prop="metric_type" label="类型" width="120" />
            <el-table-column prop="file_name" label="文件" min-width="180" />
            <el-table-column label="结果" width="140">
              <template #default="{ row }">
                <span>{{ row.success_rows }}/{{ row.total_rows }}</span>
              </template>
            </el-table-column>
            <el-table-column label="错误预览" min-width="240">
              <template #default="{ row }">
                <div v-if="row.error_preview.length === 0" class="ok-text">无</div>
                <div v-else class="error-stack">
                  <div v-for="item in row.error_preview" :key="item">{{ item }}</div>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.import-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.import-overview__card {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid #dfe9f2;
  background: #ffffff;
  display: grid;
  gap: 6px;
}

.import-overview__card span {
  font-size: 12px;
  color: #7a8ca2;
}

.import-overview__card strong {
  font-size: 24px;
  color: #243854;
}

.import-overview__card small {
  color: #8a99ae;
  font-size: 12px;
}

.import-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.import-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.import-subtitle {
  margin-top: 4px;
  color: #617b96;
  font-size: 13px;
  line-height: 1.6;
  max-width: 760px;
}

.import-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.import-grid {
  display: grid;
  grid-template-columns: minmax(320px, 380px) 1fr;
  gap: 16px;
}

.import-auto-card {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #d7e6fb;
  background: linear-gradient(180deg, #f9fbff 0%, #f3f7ff 100%);
  display: grid;
  gap: 12px;
}

.import-auto-card__text {
  color: #55697f;
  line-height: 1.7;
  font-size: 13px;
}

.mapping-panel {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid #d9e4f3;
  background: rgba(255, 255, 255, 0.82);
  display: grid;
  gap: 12px;
}

.mapping-panel__title {
  font-size: 13px;
  font-weight: 700;
  color: #243854;
}

.mapping-list {
  display: grid;
  gap: 10px;
}

.mapping-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: start;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid #e1eaf1;
  background: #ffffff;
}

.mapping-item__body {
  display: grid;
  gap: 4px;
}

.mapping-item__body strong {
  font-size: 13px;
  color: #243854;
}

.mapping-item__body span {
  font-size: 12px;
  line-height: 1.6;
  color: #6d8199;
}

.mapping-panel__hint {
  font-size: 12px;
  line-height: 1.7;
  color: #60778f;
}

.import-auto-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.import-auto-card__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.import-auto-card__stat {
  padding: 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e1eaf1;
  display: grid;
  gap: 4px;
}

.import-auto-card__stat span {
  font-size: 12px;
  color: #7a8ca2;
}

.import-auto-card__stat strong {
  font-size: 22px;
  color: #243854;
}

.import-panel {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid #dfe9f2;
  background: linear-gradient(180deg, #fbfdff, #f6f9fc);
}

.import-panel--history {
  min-width: 0;
}

.panel-mini-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-ink);
  margin-bottom: 14px;
}

.guide-panel {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #dfe9f2;
  background: #fbfdff;
}

.import-result-card {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #d7e6fb;
  background: linear-gradient(180deg, #f9fbff 0%, #f3f7ff 100%);
  display: grid;
  gap: 14px;
}

.import-result-card__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.import-result-card__metric {
  padding: 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e1eaf1;
  display: grid;
  gap: 4px;
}

.import-result-card__metric span {
  font-size: 12px;
  color: #7a8ca2;
}

.import-result-card__metric strong {
  font-size: 22px;
  color: #243854;
}

.import-result-card__next {
  color: #55697f;
  line-height: 1.7;
}

.import-result-card__actions {
  display: flex;
  justify-content: flex-end;
}

.guide-summary {
  color: #4f6c89;
  font-size: 13px;
  line-height: 1.7;
  margin-bottom: 12px;
}

.guide-block {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.guide-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-ink);
}

.guide-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.guide-chip {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #dfe9f2;
  background: #f5f8fc;
  color: #5d7390;
  font-size: 12px;
  line-height: 1;
}

.guide-chip--blue {
  background: #eef5ff;
  border-color: #cfe0fb;
  color: #476da8;
}

.guide-chip--soft {
  background: #f7faff;
}

.guide-next {
  padding: 12px 14px;
  border-radius: 16px;
  background: #eef5fb;
  color: #47627d;
  font-size: 13px;
  line-height: 1.6;
}

.import-hint {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: #eef5fb;
  color: #4f6c89;
  font-size: 13px;
  line-height: 1.6;
}

.import-hint--merge {
  border: 1px dashed #cfdaea;
  background: #f8fbff;
}

.import-tip-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: #637995;
  font-size: 13px;
  font-weight: 700;
}

.ok-text {
  color: #4b9c68;
}

.error-stack {
  display: grid;
  gap: 4px;
  color: #c45b54;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .import-overview {
    grid-template-columns: 1fr;
  }

  .import-grid {
    grid-template-columns: 1fr;
  }

  .import-auto-card__stats,
  .import-result-card__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
