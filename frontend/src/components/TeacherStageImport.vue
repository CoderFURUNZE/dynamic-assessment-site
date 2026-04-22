<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { CircleCheck, Files, FolderOpened, Promotion, UploadFilled } from "@element-plus/icons-vue";
import { api } from "../api";
import HintButton from "./HintButton.vue";

type Stage = { id: number; title: string; stage_order: number };
type ImportBatch = {
  id: number;
  stage_title: string;
  metric_type: string;
  file_name: string;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  error_preview: string[];
  created_at: string;
};
type MetricGuide = {
  metric_type: string;
  summary: string;
  template_fields: string[];
  affected_dimensions: string[];
  affected_indicators: string[];
  next_action: string;
};
type ImportResult = {
  batch_id?: number;
  total_rows: number;
  success_rows: number;
  failed_rows?: number;
  recalculated_users: number;
  next_action: string;
  errors?: string[];
  import_summary?: {
    stage_title?: string;
    quality_status?: string;
    recalculation_scope?: string;
    quality_hint?: string;
    enabled_sources?: string[];
    batch_ids?: number[];
  };
};
type InternalSummary = {
  summary: {
    student_count: number;
    video_students: number;
    practice_students: number;
    recommendation_students: number;
  };
  rows: Array<{
    username: string;
    student_no: string;
    watched_minutes: number;
    practice_accuracy: number;
    practice_attempts: number;
    course_mastery: number;
    dynamic_score: number;
    risk_level: string;
  }>;
};
type ImportType = "system" | "manual" | "behavior";

const props = defineProps<{ courseId: number | null; subject: string; grade: string }>();
const emit = defineEmits<{ (e: "view-profiles"): void }>();

const loading = ref(false);
const uploading = ref(false);
const behaviorApplying = ref(false);
const stages = ref<Stage[]>([]);
const batches = ref<ImportBatch[]>([]);
const metricGuides = ref<MetricGuide[]>([]);
const selectedStageId = ref<number | null>(null);
const metricType = ref("video");
const uploadFile = ref<File | null>(null);
const lastResult = ref<ImportResult | null>(null);
const internalSummary = ref<InternalSummary | null>(null);
const importType = ref<ImportType>("system");
const historyAnchor = ref<HTMLElement | null>(null);
const systemMappings = reactive({ video: true, practice: true, mastery: true });
const showCompleted = ref(false);

const metricOptions = [
  { label: "视频学习记录", value: "video" },
  { label: "作业完成记录", value: "assignment" },
  { label: "小测成绩记录", value: "quiz" },
  { label: "考勤记录", value: "attendance" },
  { label: "任务完成记录", value: "task" },
  { label: "课堂参与记录", value: "participation" },
];

const importTypeCards = [
  { value: "system" as const, title: "系统汇总数据", tag: "推荐", icon: Promotion, desc: "自动汇总平台已有的学习、练习与掌握度数据。" },
  { value: "manual" as const, title: "教师补录文件", tag: "补充", icon: FolderOpened, desc: "补充线下记录或人工整理的阶段数据文件。" },
  { value: "behavior" as const, title: "行为信号数据", tag: "进阶", icon: Files, desc: "整合行为事件与注意力信号，补充动态画像输入。" },
];

const metricTypeLabels: Record<string, string> = {
  video: "视频学习记录",
  assignment: "作业完成记录",
  quiz: "小测成绩记录",
  attendance: "考勤记录",
  task: "任务完成记录",
  participation: "课堂参与记录",
  behavior_signal: "行为信号汇总",
};

const sourceCards = computed(() => [
  { key: "video" as const, title: "视频学习", desc: "汇总观看时长与学习记录", icon: Promotion },
  { key: "practice" as const, title: "练习表现", desc: "汇总练习次数与正确率", icon: Files },
  { key: "mastery" as const, title: "掌握度变化", desc: "更新知识掌握度趋势", icon: CircleCheck },
]);

const selectedStageLabel = computed(() => stages.value.find((item) => item.id === selectedStageId.value)?.title || "未选择阶段");
const latestBatch = computed(() => batches.value[0] ?? null);
const selectedGuide = computed(() => metricGuides.value.find((item) => item.metric_type === metricType.value) ?? null);
const canUploadManual = computed(() => Boolean(props.courseId && selectedStageId.value && uploadFile.value));
const enabledSystemMappings = computed(() => Object.values(systemMappings).filter(Boolean).length);
const currentModeLabel = computed(() => importTypeCards.find((item) => item.value === importType.value)?.title || "系统汇总数据");
const currentModeDesc = computed(() => importTypeCards.find((item) => item.value === importType.value)?.desc || "");
const latestBatchLabel = computed(() => (latestBatch.value ? latestBatch.value.created_at.replace("T", " ").slice(0, 16) : "暂无导入记录"));
const historyCountLabel = computed(() => `${batches.value.length} 条记录`);
const resultStatus = computed(() => ((lastResult.value?.recalculated_users ?? 0) > 0 ? "已更新画像" : "待更新画像"));
const uploadTip = computed(() => {
  if (importType.value === "system") return `已选择 ${enabledSystemMappings.value} 项系统来源，导入后将更新当前阶段画像。`;
  if (importType.value === "manual") return selectedGuide.value?.summary || "上传后会覆盖当前阶段同类文件数据。";
  return "当前行为信号使用平台已采集数据，无需上传文件，开始导入后会直接汇总到当前阶段。";
});

const fileMeta = computed(() => {
  if (!uploadFile.value) return null;
  const sizeMb = uploadFile.value.size / 1024 / 1024;
  return {
    name: uploadFile.value.name,
    size: `${sizeMb >= 1 ? sizeMb.toFixed(2) : (uploadFile.value.size / 1024).toFixed(1)} ${sizeMb >= 1 ? "MB" : "KB"}`,
  };
});

const recentBatches = computed(() => batches.value.slice(0, 5));
const checklist = computed(() => [
  { key: "stage", title: "选择阶段", desc: selectedStageLabel.value, done: Boolean(selectedStageId.value) },
  { key: "type", title: "选择导入方式", desc: currentModeLabel.value, done: true },
  {
    key: "config",
    title: importType.value === "manual" ? "上传导入文件" : importType.value === "system" ? "选择系统来源" : "确认行为信号导入",
    desc:
      importType.value === "manual"
        ? fileMeta.value?.name || "待上传文件"
        : importType.value === "system"
          ? `已选 ${enabledSystemMappings.value} 项来源`
          : "使用平台采集的行为数据",
    done: importType.value === "manual" ? Boolean(uploadFile.value) : importType.value === "system" ? enabledSystemMappings.value > 0 : true,
  },
  { key: "result", title: "完成一次导入", desc: latestBatchLabel.value, done: Boolean(latestBatch.value) },
]);
const pendingItems = computed(() => checklist.value.filter((item) => !item.done));
const completedItems = computed(() => checklist.value.filter((item) => item.done));
const completionPercent = computed(() => Math.round((completedItems.value.length / Math.max(checklist.value.length, 1)) * 100));

const resultSummaryCards = computed(() => {
  if (!lastResult.value) return [];
  return [
    { label: "导入成功", value: String(lastResult.value.success_rows) },
    { label: "导入失败", value: String(lastResult.value.failed_rows ?? 0) },
    { label: "覆盖学生", value: String(lastResult.value.recalculated_users) },
    { label: "画像状态", value: resultStatus.value },
  ];
});

const sourceSummaryCards = computed(() => {
  if (!internalSummary.value) return [];
  return [
    { label: "覆盖学生", value: String(internalSummary.value.summary.student_count) },
    { label: "视频数据", value: String(internalSummary.value.summary.video_students) },
    { label: "练习数据", value: String(internalSummary.value.summary.practice_students) },
    { label: "推荐数据", value: String(internalSummary.value.summary.recommendation_students) },
  ];
});

async function loadGuides() {
  metricGuides.value = (await api.get("/stages/metric-guides")).data ?? [];
}

async function loadStages() {
  if (!props.courseId) {
    stages.value = [];
    selectedStageId.value = null;
    return;
  }
  stages.value = (await api.get(`/stages/courses/${props.courseId}`)).data ?? [];
  if (!stages.value.some((item) => item.id === selectedStageId.value)) selectedStageId.value = stages.value[0]?.id ?? null;
}

async function loadBatches() {
  if (!props.courseId) {
    batches.value = [];
    return;
  }
  const query = new URLSearchParams({ course_id: String(props.courseId) });
  if (selectedStageId.value) query.set("stage_id", String(selectedStageId.value));
  batches.value = (await api.get(`/stages/imports?${query.toString()}`)).data ?? [];
}

async function loadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) {
    internalSummary.value = null;
    return;
  }
  internalSummary.value = (await api.get(`/stages/internal-summary?course_id=${props.courseId}&stage_id=${selectedStageId.value}`)).data ?? null;
}

async function refresh() {
  loading.value = true;
  try {
    await loadGuides();
    await loadStages();
    await loadBatches();
    await loadInternalSummary();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载导入数据失败");
  } finally {
    loading.value = false;
  }
}

function onFileChange(file: any) {
  uploadFile.value = file?.raw ?? null;
}

function onFileRemove() {
  uploadFile.value = null;
}

function toggleSystemMapping(key: keyof typeof systemMappings) {
  systemMappings[key] = !systemMappings[key];
}

function scrollToHistory() {
  nextTick(() => historyAnchor.value?.scrollIntoView({ behavior: "smooth", block: "start" }));
}

async function uploadManual() {
  if (!canUploadManual.value || !props.courseId || !selectedStageId.value || !uploadFile.value) {
    ElMessage.warning("请先选择阶段并上传文件");
    return;
  }
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("metric_type", metricType.value);
  form.append("file", uploadFile.value);
  uploading.value = true;
  try {
    const data = (await api.post("/stages/imports/upload", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data;
    uploadFile.value = null;
    await loadBatches();
    ElMessage.success(`导入完成，成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条`);
    scrollToHistory();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导入失败");
  } finally {
    uploading.value = false;
  }
}

async function applyInternalSummary() {
  if (!props.courseId || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("include_video", String(systemMappings.video));
  form.append("include_practice", String(systemMappings.practice));
  form.append("include_mastery", String(systemMappings.mastery));
  uploading.value = true;
  try {
    const data = (await api.post("/stages/internal-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data;
    await loadBatches();
    await loadInternalSummary();
    ElMessage.success("系统汇总导入完成");
    scrollToHistory();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "系统汇总导入失败");
  } finally {
    uploading.value = false;
  }
}

async function applyBehavior() {
  if (!props.courseId || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  behaviorApplying.value = true;
  try {
    lastResult.value = (await api.post("/stages/internal-behavior-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } })).data ?? null;
    await loadBatches();
    ElMessage.success("行为信号导入完成");
    scrollToHistory();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "行为信号导入失败");
  } finally {
    behaviorApplying.value = false;
  }
}

async function downloadTemplate() {
  try {
    const res = await api.get(`/stages/template?metric_type=${encodeURIComponent(metricType.value)}`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `stage_template_${metricType.value}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "模板下载失败");
  }
}

async function downloadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  try {
    const res = await api.get(`/stages/internal-summary/export?course_id=${props.courseId}&stage_id=${selectedStageId.value}`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `internal_stage_summary_${props.courseId}_${selectedStageId.value}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "汇总导出失败");
  }
}

function openProfiles() {
  emit("view-profiles");
}

function handleExternalStageChange(event: Event) {
  const custom = event as CustomEvent<{ courseId?: number | null }>;
  const changedCourseId = Number(custom.detail?.courseId || 0);
  if (props.courseId && (!changedCourseId || changedCourseId === Number(props.courseId))) {
    refresh().catch((e: any) => ElMessage.error(e?.response?.data?.detail ?? "刷新导入数据失败"));
  }
}

watch(() => props.courseId, refresh, { immediate: true });
watch(selectedStageId, () => {
  loadBatches().catch(() => undefined);
  loadInternalSummary().catch(() => undefined);
});
onMounted(() => window.addEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener));
onBeforeUnmount(() => window.removeEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener));
</script>

<template>
  <section class="import-workspace" v-loading="loading">
    <div v-if="!courseId" class="import-empty panel-card">
      <el-empty description="当前课程下暂无可导入阶段" />
    </div>

    <template v-else>
      <section class="import-shell">
        <div class="import-main panel-card">
          <section class="import-hero">
            <div>
              <span class="section-eyebrow">阶段导入</span>
              <h2>把系统数据、补录文件和行为信号接到同一条评价链</h2>
              <p>按阶段导入后，系统会同步更新学生画像、学习风险与后续推荐依据。</p>
            </div>
            <div class="import-hero__badges">
              <span>{{ subject || "未选择课程" }}</span>
              <span>{{ selectedStageLabel }}</span>
              <span>{{ currentModeLabel }}</span>
            </div>
          </section>

          <div class="type-grid">
            <button
              v-for="item in importTypeCards"
              :key="item.value"
              type="button"
              class="type-card"
              :class="{ 'is-active': importType === item.value }"
              @click="importType = item.value"
            >
              <div class="type-card__icon">
                <el-icon><component :is="item.icon" /></el-icon>
              </div>
              <div class="type-card__copy">
                <span class="type-card__tag">{{ item.tag }}</span>
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
            </button>
          </div>

          <section class="config-card">
            <div class="config-card__head">
              <div>
                <span class="section-eyebrow">配置与执行</span>
                <h3>先配好阶段与来源，再开始导入</h3>
                <p>{{ uploadTip }}</p>
              </div>
              <div class="config-card__actions">
                <HintButton v-if="importType === 'system'" size="small" tip="导出当前阶段系统汇总 CSV" @click="downloadInternalSummary">下载汇总</HintButton>
                <HintButton v-if="importType !== 'system'" size="small" tip="下载当前导入模板" @click="downloadTemplate">下载模板</HintButton>
              </div>
            </div>

            <div class="config-grid">
              <div class="field-block field-block--full">
                <label>阶段</label>
                <el-select v-model="selectedStageId" size="large" placeholder="请选择阶段">
                  <el-option v-for="item in stages" :key="item.id" :label="`${item.stage_order}. ${item.title}`" :value="item.id" />
                </el-select>
              </div>

              <template v-if="importType === 'system'">
                <div class="field-block field-block--full">
                  <label>系统来源</label>
                  <div class="source-grid">
                    <button
                      v-for="item in sourceCards"
                      :key="item.key"
                      type="button"
                      class="source-card"
                      :class="{ 'is-active': systemMappings[item.key] }"
                      @click="toggleSystemMapping(item.key)"
                    >
                      <div class="source-card__meta">
                        <el-icon><component :is="item.icon" /></el-icon>
                        <div>
                          <strong>{{ item.title }}</strong>
                          <span>{{ item.desc }}</span>
                        </div>
                      </div>
                      <el-switch :model-value="systemMappings[item.key]" @click.stop />
                    </button>
                  </div>
                </div>
              </template>

              <template v-else-if="importType === 'manual'">
                <div class="field-block">
                  <label>数据类型</label>
                  <el-select v-model="metricType" size="large">
                    <el-option v-for="item in metricOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </div>

                <div class="field-block field-block--full">
                  <label>上传文件</label>
                  <el-upload class="upload-dropzone" drag :auto-upload="false" :show-file-list="false" :limit="1" accept=".csv,.xlsx" @change="onFileChange">
                    <el-icon class="upload-dropzone__icon"><UploadFilled /></el-icon>
                    <div class="upload-dropzone__title">拖拽文件到此，或点击上传</div>
                    <div class="upload-dropzone__desc">支持 CSV / XLSX</div>
                  </el-upload>

                  <div v-if="fileMeta" class="file-card">
                    <div class="file-card__meta">
                      <strong>{{ fileMeta.name }}</strong>
                      <span>{{ fileMeta.size }}</span>
                    </div>
                    <button class="ghost-btn" type="button" @click="onFileRemove">移除</button>
                  </div>
                </div>
              </template>

              <template v-else>
                <div class="field-block field-block--full">
                  <label>行为信号汇总</label>
                  <div class="behavior-placeholder">
                    <el-icon><Files /></el-icon>
                    <div>
                      <strong>使用平台已采集的行为数据</strong>
                      <span>系统会汇总行为事件、注意力信号与动态变化，直接补充阶段画像。</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <div class="config-footer">
              <div class="config-tip">{{ currentModeDesc }}</div>
              <div class="config-footer__actions">
                <HintButton v-if="importType === 'system'" type="primary" :loading="uploading" tip="执行系统汇总导入" @click="applyInternalSummary">开始导入</HintButton>
                <HintButton v-else-if="importType === 'manual'" type="primary" :disabled="!canUploadManual" :loading="uploading" tip="上传文件并开始导入" @click="uploadManual">开始导入</HintButton>
                <HintButton v-else type="primary" :loading="behaviorApplying" tip="汇总行为信号并生成阶段画像" @click="applyBehavior">开始导入</HintButton>
              </div>
            </div>

            <div v-if="selectedGuide && importType === 'manual'" class="guide-box">
              <div>
                <strong>模板说明</strong>
                <p>{{ selectedGuide.summary }}</p>
              </div>
              <div class="guide-chips">
                <span v-for="field in selectedGuide.template_fields" :key="field">{{ field }}</span>
              </div>
            </div>
          </section>
        </div>

        <aside class="import-side">
          <section class="side-card panel-card">
            <span class="section-eyebrow">当前进度</span>
            <div class="side-progress">
              <strong>{{ completionPercent }}%</strong>
              <span>还差 {{ pendingItems.length }} 项待补充</span>
            </div>
            <div class="side-checks">
              <article v-for="item in pendingItems" :key="item.key" class="side-check side-check--pending">
                <strong>{{ item.title }}</strong>
                <span>{{ item.desc }}</span>
              </article>
            </div>
            <button class="side-toggle" type="button" @click="showCompleted = !showCompleted">
              已完成 {{ completedItems.length }} 项
              <span>{{ showCompleted ? "收起" : "展开" }}</span>
            </button>
            <div v-if="showCompleted" class="side-checks side-checks--done">
              <article v-for="item in completedItems" :key="item.key" class="side-check side-check--done">
                <strong>{{ item.title }}</strong>
                <span>{{ item.desc }}</span>
              </article>
            </div>
          </section>

          <section class="side-card panel-card">
            <span class="section-eyebrow">课程摘要</span>
            <div class="side-summary">
              <div><small>课程</small><strong>{{ subject || "未选择课程" }}</strong></div>
              <div><small>阶段</small><strong>{{ selectedStageLabel }}</strong></div>
              <div><small>导入方式</small><strong>{{ currentModeLabel }}</strong></div>
              <div><small>最近导入</small><strong>{{ latestBatchLabel }}</strong></div>
            </div>
          </section>

          <section class="side-card panel-card">
            <span class="section-eyebrow">快捷操作</span>
            <div class="side-actions">
              <HintButton size="small" tip="刷新当前课程的导入数据" @click="refresh">刷新</HintButton>
              <HintButton size="small" tip="查看最近导入记录" @click="scrollToHistory">查看历史</HintButton>
              <HintButton size="small" tip="前往结果页复核画像" @click="openProfiles">查看结果</HintButton>
            </div>
          </section>
        </aside>
      </section>

      <section class="panel-card result-card">
        <div class="result-card__head">
          <div>
            <span class="section-eyebrow">导入结果</span>
            <h3>查看本次导入结果</h3>
            <p>导入完成后，这里会显示成功数、失败数、画像更新状态与下一步建议。</p>
          </div>
          <HintButton size="small" tip="查看完整导入历史" @click="scrollToHistory">查看导入历史</HintButton>
        </div>

        <div v-if="!lastResult" class="result-strip">
          暂无本次导入结果。完成一次导入后，这里会立即显示结果摘要与下一步动作。
        </div>

        <template v-else>
          <div class="result-grid">
            <div v-for="item in resultSummaryCards" :key="item.label" class="result-summary">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>

          <div class="result-note">
            <span>{{ lastResult.next_action }}</span>
            <button class="ghost-btn" type="button" @click="openProfiles">去结果页复核</button>
          </div>

          <div v-if="lastResult.errors?.length" class="error-box">
            <strong>错误预览</strong>
            <span v-for="msg in lastResult.errors" :key="msg">{{ msg }}</span>
          </div>
        </template>
      </section>

      <section v-if="sourceSummaryCards.length" class="panel-card source-card-panel">
        <div class="result-card__head">
          <div>
            <span class="section-eyebrow">系统汇总预览</span>
            <h3>当前阶段可用数据规模</h3>
            <p>帮助教师快速判断当前系统数据是否足够支撑阶段画像更新。</p>
          </div>
        </div>
        <div class="result-grid">
          <div v-for="item in sourceSummaryCards" :key="item.label" class="result-summary">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>

      <section ref="historyAnchor" class="panel-card history-card">
        <div class="result-card__head">
          <div>
            <span class="section-eyebrow">历史记录</span>
            <h3>最近导入记录</h3>
            <p>保留最近导入结果，便于阶段复盘、错误排查和过程留痕。</p>
          </div>
          <div class="history-card__meta">{{ historyCountLabel }}</div>
        </div>

        <el-table :data="recentBatches" size="large" style="width: 100%">
          <el-table-column label="时间" min-width="180">
            <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 19) }}</template>
          </el-table-column>
          <el-table-column prop="stage_title" label="阶段" min-width="220" />
          <el-table-column label="类型" min-width="160">
            <template #default="{ row }"><span class="history-badge">{{ metricTypeLabels[row.metric_type] || row.metric_type }}</span></template>
          </el-table-column>
          <el-table-column prop="file_name" label="文件" min-width="220" />
          <el-table-column label="成功/总数" min-width="120">
            <template #default="{ row }">{{ row.success_rows }}/{{ row.total_rows }}</template>
          </el-table-column>
          <el-table-column label="错误预览" min-width="260">
            <template #default="{ row }">
              <span v-if="!row.error_preview?.length" class="history-ok">无</span>
              <div v-else class="history-errors" :title="row.error_preview.join('\n')">{{ row.error_preview.join("；") }}</div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>
  </section>
</template>

<style scoped>
.import-workspace {
  display: grid;
  gap: 18px;
}

.panel-card {
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
}

.section-eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #eefbf3;
  color: #166534;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  width: fit-content;
}

.import-empty {
  padding: 24px;
}

.import-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
  align-items: start;
}

.import-main {
  display: grid;
  gap: 22px;
  padding: 24px;
}

.import-hero,
.config-card__head,
.result-card__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.import-hero h2,
.config-card__head h3,
.result-card__head h3 {
  margin: 8px 0 0;
  color: #1f2937;
  font-size: 28px;
  line-height: 1.15;
}

.import-hero p,
.config-card__head p,
.result-card__head p {
  margin: 10px 0 0;
  color: #6a7280;
  line-height: 1.75;
}

.import-hero__badges {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.import-hero__badges span,
.history-badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.type-grid,
.source-grid,
.result-grid {
  display: grid;
  gap: 14px;
}

.type-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.type-card,
.source-card,
.result-summary,
.side-check,
.file-card,
.behavior-placeholder,
.guide-box {
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #ffffff;
}

.type-card,
.source-card {
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.type-card {
  display: grid;
  gap: 12px;
  padding: 18px;
  text-align: left;
}

.type-card.is-active,
.source-card.is-active {
  border-color: rgba(34, 197, 94, 0.28);
  background: #f0fdf4;
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.08);
}

.type-card__icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: rgba(191, 227, 245, 0.45);
  color: #334155;
}

.type-card__tag {
  display: inline-flex;
  width: fit-content;
  min-height: 28px;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  background: #eefbf3;
  color: #166534;
  font-size: 12px;
  font-weight: 800;
}

.type-card strong,
.source-card__meta strong,
.result-summary strong,
.side-check strong,
.file-card__meta strong,
.guide-box strong,
.behavior-placeholder strong,
.side-summary strong,
.side-progress strong {
  color: #1f2937;
}

.type-card p,
.source-card__meta span,
.result-summary span,
.side-check span,
.file-card__meta span,
.guide-box p,
.behavior-placeholder span,
.side-summary small,
.side-progress span,
.config-tip,
.result-strip,
.result-note span,
.history-card__meta {
  color: #6a7280;
  line-height: 1.7;
}

.config-card {
  display: grid;
  gap: 18px;
  padding: 22px;
  border-radius: 28px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #ffffff;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field-block {
  display: grid;
  gap: 10px;
}

.field-block--full {
  grid-column: 1 / -1;
}

.field-block label {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.source-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.source-card {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 16px;
  text-align: left;
}

.source-card__meta {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.source-card__meta .el-icon,
.behavior-placeholder .el-icon {
  margin-top: 2px;
  color: #16a34a;
  font-size: 18px;
}

.upload-dropzone {
  width: 100%;
}

:deep(.upload-dropzone .el-upload-dragger) {
  width: 100%;
  padding: 34px 18px;
  border-radius: 22px;
  border: 1px dashed rgba(148, 163, 184, 0.28);
  background: #f8fafc;
}

.upload-dropzone__icon {
  margin-bottom: 10px;
  color: #16a34a;
  font-size: 28px;
}

.upload-dropzone__title {
  color: #1f2937;
  font-size: 16px;
  font-weight: 700;
}

.upload-dropzone__desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.file-card,
.behavior-placeholder,
.guide-box {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 16px;
}

.file-card__meta,
.behavior-placeholder > div {
  display: grid;
  gap: 4px;
}

.ghost-btn,
.side-toggle {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #ffffff;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.config-footer,
.config-footer__actions,
.side-actions,
.result-note {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.config-footer {
  justify-content: space-between;
}

.guide-box {
  display: grid;
  gap: 12px;
}

.guide-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.guide-chips span {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.import-side {
  display: grid;
  gap: 18px;
}

.side-card {
  display: grid;
  gap: 16px;
  padding: 20px;
}

.side-progress {
  display: grid;
  gap: 4px;
}

.side-progress strong {
  font-size: 32px;
  line-height: 1;
}

.side-checks {
  display: grid;
  gap: 10px;
}

.side-check {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
}

.side-check--pending {
  border-color: rgba(245, 158, 11, 0.2);
}

.side-check--done {
  border-color: rgba(34, 197, 94, 0.18);
}

.side-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.side-summary {
  display: grid;
  gap: 12px;
}

.side-summary > div {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #f8fafc;
}

.result-card,
.source-card-panel,
.history-card {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.result-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.result-summary {
  display: grid;
  gap: 6px;
  padding: 16px;
}

.result-summary strong {
  font-size: 26px;
  line-height: 1.1;
}

.result-strip,
.error-box {
  padding: 16px 18px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #f8fafc;
}

.error-box {
  display: grid;
  gap: 8px;
}

.history-card :deep(.el-table) {
  --el-table-header-bg-color: #f8fbff;
  --el-table-row-hover-bg-color: rgba(239, 246, 255, 0.72);
  border-radius: 20px;
  overflow: hidden;
}

.history-ok {
  color: #15803d;
  font-weight: 700;
}

.history-errors {
  color: #9a3412;
  line-height: 1.6;
}

@media (max-width: 1200px) {
  .import-shell {
    grid-template-columns: 1fr;
  }

  .type-grid,
  .source-grid,
  .result-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .import-main,
  .side-card,
  .result-card,
  .source-card-panel,
  .history-card {
    padding: 18px;
  }

  .import-hero h2,
  .config-card__head h3,
  .result-card__head h3 {
    font-size: 22px;
  }

  .type-grid,
  .source-grid,
  .result-grid,
  .config-grid {
    grid-template-columns: 1fr;
  }

  .config-footer {
    align-items: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .type-card,
  .source-card {
    transition: none;
  }
}
</style>
