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
const historyShell = ref<HTMLElement | null>(null);
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
  { value: "system" as const, title: "系统汇总数据", tag: "推荐", icon: Promotion, desc: "自动汇总平台已有的视频、练习和掌握度数据" },
  { value: "manual" as const, title: "教师补录文件", tag: "补充", icon: FolderOpened, desc: "补充线下记录或人工整理的阶段数据文件" },
  { value: "behavior" as const, title: "行为信号数据", tag: "进阶", icon: Files, desc: "导入行为事件与注意力信号，补充动态画像输入" },
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
  { key: "video" as const, title: "视频学习", desc: "汇总观看与学习记录", icon: Promotion },
  { key: "practice" as const, title: "练习表现", desc: "同步练习次数与正确率", icon: Files },
  { key: "mastery" as const, title: "掌握度变化", desc: "更新知识掌握趋势", icon: CircleCheck },
]);

const selectedStageLabel = computed(() => stages.value.find((item) => item.id === selectedStageId.value)?.title || "未选择阶段");
const latestBatch = computed(() => batches.value[0] ?? null);
const selectedGuide = computed(() => metricGuides.value.find((item) => item.metric_type === metricType.value) ?? null);
const canUploadManual = computed(() => Boolean(props.courseId && selectedStageId.value && uploadFile.value));
const enabledSystemMappings = computed(() => Object.values(systemMappings).filter(Boolean).length);
const currentModeLabel = computed(() => importTypeCards.find((item) => item.value === importType.value)?.title || "系统汇总数据");
const currentModeDesc = computed(() => importTypeCards.find((item) => item.value === importType.value)?.desc || "");
const latestBatchLabel = computed(() => latestBatch.value ? latestBatch.value.created_at.replace("T", " ").slice(0, 16) : "暂无导入记录");
const historyCountLabel = computed(() => `${batches.value.length} 条记录`);
const resultStatus = computed(() => ((lastResult.value?.recalculated_users ?? 0) > 0 ? "已更新画像" : "待更新画像"));
const uploadTip = computed(() => {
  if (importType.value === "system") return `已选择 ${enabledSystemMappings.value} 项数据来源，导入后将更新当前阶段画像。`;
  if (importType.value === "manual") return selectedGuide.value?.summary || "上传后会覆盖当前阶段的同类文件数据。";
  return "当前行为信号使用系统已采集数据，无需上传文件，开始导入后会直接汇总到当前阶段。";
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
  { key: "type", title: "选择导入类型", desc: currentModeLabel.value, done: true },
  {
    key: "config",
    title: importType.value === "manual" ? "上传导入文件" : importType.value === "system" ? "选择系统来源" : "确认行为信号导入",
    desc: importType.value === "manual" ? (fileMeta.value?.name || "待上传文件") : importType.value === "system" ? `已选 ${enabledSystemMappings.value} 项来源` : "使用平台采集的行为数据",
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

async function loadGuides() { metricGuides.value = (await api.get("/stages/metric-guides")).data ?? []; }
async function loadStages() {
  if (!props.courseId) { stages.value = []; selectedStageId.value = null; return; }
  stages.value = (await api.get(`/stages/courses/${props.courseId}`)).data ?? [];
  if (!stages.value.some((item) => item.id === selectedStageId.value)) selectedStageId.value = stages.value[0]?.id ?? null;
}
async function loadBatches() {
  if (!props.courseId) { batches.value = []; return; }
  const query = new URLSearchParams({ course_id: String(props.courseId) });
  if (selectedStageId.value) query.set("stage_id", String(selectedStageId.value));
  batches.value = (await api.get(`/stages/imports?${query.toString()}`)).data ?? [];
}
async function loadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) { internalSummary.value = null; return; }
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
  } finally { loading.value = false; }
}
function onFileChange(file: any) { uploadFile.value = file?.raw ?? null; }
function onFileRemove() { uploadFile.value = null; }
function toggleSystemMapping(key: keyof typeof systemMappings) { systemMappings[key] = !systemMappings[key]; }
function scrollToHistory() { nextTick(() => historyAnchor.value?.scrollIntoView({ behavior: "smooth", block: "start" })); }
async function uploadManual() {
  if (!canUploadManual.value || !props.courseId || !selectedStageId.value || !uploadFile.value) return ElMessage.warning("请先选择上传文件");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("metric_type", metricType.value);
  form.append("file", uploadFile.value);
  uploading.value = true;
  try {
    const data = (await api.post("/stages/imports/upload", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data; uploadFile.value = null; await loadBatches();
    ElMessage.success(`导入完成，成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条`);
    scrollToHistory();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "导入失败"); } finally { uploading.value = false; }
}
async function applyInternalSummary() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("include_video", String(systemMappings.video));
  form.append("include_practice", String(systemMappings.practice));
  form.append("include_mastery", String(systemMappings.mastery));
  uploading.value = true;
  try {
    const data = (await api.post("/stages/internal-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data; await loadBatches(); await loadInternalSummary();
    ElMessage.success("系统汇总导入完成"); scrollToHistory();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "系统汇总导入失败"); } finally { uploading.value = false; }
}
async function applyBehavior() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  behaviorApplying.value = true;
  try {
    lastResult.value = (await api.post("/stages/internal-behavior-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } })).data ?? null;
    await loadBatches(); ElMessage.success("行为信号导入完成"); scrollToHistory();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "行为信号导入失败"); } finally { behaviorApplying.value = false; }
}
async function downloadTemplate() {
  try {
    const res = await api.get(`/stages/template?metric_type=${encodeURIComponent(metricType.value)}`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = `stage_template_${metricType.value}.csv`; link.click(); window.URL.revokeObjectURL(url);
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "模板下载失败"); }
}
async function downloadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  try {
    const res = await api.get(`/stages/internal-summary/export?course_id=${props.courseId}&stage_id=${selectedStageId.value}`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = `internal_stage_summary_${props.courseId}_${selectedStageId.value}.csv`; link.click(); window.URL.revokeObjectURL(url);
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "汇总导出失败"); }
}
function openProfiles() { emit("view-profiles"); }
function handleExternalStageChange(event: Event) {
  const custom = event as CustomEvent<{ courseId?: number | null }>;
  const changedCourseId = Number(custom.detail?.courseId || 0);
  if (props.courseId && (!changedCourseId || changedCourseId === Number(props.courseId))) {
    refresh().catch((e: any) => ElMessage.error(e?.response?.data?.detail ?? "刷新导入数据失败"));
  }
}
watch(() => props.courseId, refresh, { immediate: true });
watch(selectedStageId, () => { loadBatches().catch(() => undefined); loadInternalSummary().catch(() => undefined); });
onMounted(() => window.addEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener));
onBeforeUnmount(() => window.removeEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener));
</script>

<template>
  <section class="import-workspace" v-loading="loading">
    <div v-if="!courseId" class="import-empty">
      <el-empty description="当前课程下暂无可导入阶段" />
    </div>

    <template v-else>
      <section class="import-shell">
        <div class="import-main panel-card">
          <section class="import-section">
            <div class="import-section__head">
              <div>
                <span class="import-section__eyebrow">步骤 1</span>
                <h2>选择本次导入内容</h2>
                <p>先明确导入来源，再进入阶段配置与上传执行。</p>
              </div>
            </div>

            <div class="type-grid">
              <button
                v-for="item in importTypeCards"
                :key="item.value"
                type="button"
                class="type-card"
                :class="{ 'is-active': importType === item.value }"
                @click="importType = item.value"
              >
                <el-icon class="type-card__icon"><component :is="item.icon" /></el-icon>
                <div class="type-card__copy">
                  <span class="type-card__tag">{{ item.tag }}</span>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.desc }}</p>
                </div>
              </button>
            </div>
          </section>

          <section class="import-section">
            <div class="import-section__head import-section__head--actions">
              <div>
                <span class="import-section__eyebrow">步骤 2</span>
                <h2>配置并开始导入</h2>
                <p>{{ uploadTip }}</p>
              </div>
              <div class="import-section__actions">
                <HintButton v-if="importType === 'system'" size="small" tip="导出系统汇总 CSV" @click="downloadInternalSummary">下载汇总</HintButton>
                <HintButton v-if="importType !== 'system'" size="small" tip="下载当前导入模板" @click="downloadTemplate">下载模板</HintButton>
              </div>
            </div>

            <div class="config-panel">
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
                    <el-upload
                      class="upload-dropzone"
                      drag
                      :auto-upload="false"
                      :show-file-list="false"
                      :limit="1"
                      accept=".csv,.xlsx"
                      @change="onFileChange"
                    >
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
                        <strong>使用平台已采集行为数据</strong>
                        <span>将汇总行为事件、注意力信号与动态变化，直接补充阶段画像。</span>
                      </div>
                    </div>
                  </div>
                </template>
              </div>

              <div class="config-actions">
                <HintButton v-if="importType === 'system'" type="primary" :loading="uploading" tip="执行系统汇总导入" @click="applyInternalSummary">开始导入</HintButton>
                <HintButton v-else-if="importType === 'manual'" type="primary" :disabled="!canUploadManual" :loading="uploading" tip="上传文件并开始导入" @click="uploadManual">开始导入</HintButton>
                <HintButton v-else type="primary" :loading="behaviorApplying" tip="汇总行为信号并生成阶段画像" @click="applyBehavior">开始导入</HintButton>
                <span class="config-tip">{{ currentModeDesc }}</span>
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
            </div>
          </section>
        </div>

        <aside class="import-side">
          <section class="side-card">
            <span class="side-card__eyebrow">当前导入摘要</span>
            <div class="side-card__summary">
              <div><small>课程</small><strong>{{ subject || "未选择课程" }}</strong></div>
              <div><small>阶段</small><strong>{{ selectedStageLabel }}</strong></div>
              <div><small>模式</small><strong>{{ currentModeLabel }}</strong></div>
              <div><small>最近导入</small><strong>{{ latestBatchLabel }}</strong></div>
            </div>
          </section>

          <section class="side-card">
            <div class="side-card__head">
              <div>
                <span class="side-card__eyebrow">当前完成度</span>
                <h3>{{ completionPercent }}%</h3>
                <p>还差 {{ pendingItems.length }} 项待补充</p>
              </div>
            </div>

            <div class="side-checks">
              <article v-for="item in pendingItems" :key="item.key" class="side-check side-check--pending">
                <div><strong>{{ item.title }}</strong><span>{{ item.desc }}</span></div>
              </article>
            </div>

            <button class="side-toggle" type="button" @click="showCompleted = !showCompleted">
              已完成 {{ completedItems.length }} 项
              <span>{{ showCompleted ? "收起" : "展开" }}</span>
            </button>

            <div v-if="showCompleted" class="side-checks side-checks--done">
              <article v-for="item in completedItems" :key="item.key" class="side-check side-check--done">
                <div><strong>{{ item.title }}</strong><span>{{ item.desc }}</span></div>
              </article>
            </div>
          </section>

          <section class="side-card">
            <span class="side-card__eyebrow">快捷操作</span>
            <div class="side-actions">
              <HintButton size="small" tip="刷新当前课程的导入数据" @click="refresh">刷新</HintButton>
              <HintButton size="small" tip="查看最近导入记录" @click="scrollToHistory">查看历史</HintButton>
              <HintButton size="small" tip="去结果页复核画像" @click="openProfiles">去看结果</HintButton>
            </div>
          </section>
        </aside>
      </section>

      <section class="result-card panel-card">
        <div class="result-card__head">
          <div>
            <span class="import-section__eyebrow">导入结果</span>
            <h2>查看本次导入结果</h2>
            <p>导入完成后，这里会显示结果摘要与下一步操作入口。</p>
          </div>
          <HintButton size="small" tip="查看完整导入历史" @click="scrollToHistory">查看导入历史</HintButton>
        </div>

        <div v-if="!lastResult" class="result-strip">
          暂无本次导入结果。完成一次导入后，这里会立即显示成功数、失败数和重算结果。
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
            <button class="ghost-btn" type="button" @click="openProfiles">去结果复核</button>
          </div>

          <div v-if="lastResult.errors?.length" class="error-box">
            <strong>错误预览</strong>
            <span v-for="msg in lastResult.errors" :key="msg">{{ msg }}</span>
          </div>
        </template>
      </section>

      <section ref="historyAnchor" class="history-card panel-card">
        <div class="history-card__head">
          <div>
            <span class="import-section__eyebrow">历史记录</span>
            <h2>导入历史</h2>
            <p>保留最近导入记录，方便回看阶段数据与最近一次操作。</p>
          </div>
          <div class="history-card__meta">{{ historyCountLabel }}</div>
        </div>

        <div ref="historyShell" class="history-table-shell">
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
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.import-workspace { display: grid; gap: 24px; }
.panel-card,.side-card { border: 3px solid #1f2937; border-radius: 30px; background: radial-gradient(circle at top right, rgba(210, 238, 255, 0.34), transparent 42%), radial-gradient(circle at top left, rgba(215, 249, 168, 0.14), transparent 28%), #fffdf6; box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12); }
.import-empty { border-radius: 30px; border: 3px solid #1f2937; background: radial-gradient(circle at top right, rgba(210, 238, 255, 0.34), transparent 42%), radial-gradient(circle at top left, rgba(215, 249, 168, 0.14), transparent 28%), #fffdf6; padding: 24px; box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12); }
.import-shell { display: grid; grid-template-columns: minmax(0,1fr) 320px; gap: 24px; align-items: start; }
.import-main { padding: 24px; display: grid; gap: 24px; }
.import-section { display: grid; gap: 18px; }
.import-section__head,.result-card__head,.history-card__head,.side-card__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.import-section__eyebrow,.side-card__eyebrow { display: inline-flex; width: fit-content; padding: 6px 12px; border-radius: 999px; background: #d7f9a8; color: #17325c; font-size: 12px; font-weight: 800; }
.import-section__head h2,.result-card__head h2,.history-card__head h2 { margin: 8px 0 0; color: #17325c; font-size: 28px; line-height: 1.2; }
.import-section__head p,.result-card__head p,.history-card__head p,.side-card p { margin: 8px 0 0; color: #70839d; line-height: 1.7; }
.type-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.type-card { display: grid; gap: 12px; padding: 20px; text-align: left; border-radius: 22px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); cursor: pointer; }
.type-card.is-active { border-color: #1f2937; background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.55), transparent 55%), #fffdf6; }
.type-card__icon { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center; background: #f5f0e7; color: #b88f46; font-size: 20px; }
.type-card__copy { display: grid; gap: 6px; }
.type-card__tag { display: inline-flex; width: fit-content; padding: 4px 10px; border-radius: 999px; background: #f5fbe8; color: #5f7a33; font-size: 12px; font-weight: 700; }
.type-card strong { color: #1f2a44; font-size: 22px; }
.type-card p { margin: 0; color: #70839d; line-height: 1.7; }
.config-panel { border-radius: 24px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); padding: 20px; display: grid; gap: 18px; }
.config-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.field-block { display: grid; gap: 10px; }
.field-block--full { grid-column: 1 / -1; }
.field-block label { font-size: 13px; font-weight: 700; color: #5f6f85; }
.source-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.source-card { display: flex; justify-content: space-between; gap: 14px; padding: 16px; border-radius: 20px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); cursor: pointer; }
.source-card.is-active { border-color: #1f2937; background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.45), transparent 52%), #fffdf6; }
.source-card__meta { display: flex; gap: 12px; align-items: flex-start; }
.source-card__meta .el-icon,.behavior-placeholder .el-icon { color: #b88f46; font-size: 18px; margin-top: 3px; }
.source-card__meta strong,.behavior-placeholder strong,.file-card__meta strong,.guide-box strong,.result-summary strong,.side-check strong { color: #1f2a44; }
.source-card__meta span,.behavior-placeholder span,.file-card__meta span,.side-check span { display: block; margin-top: 4px; color: #70839d; font-size: 13px; line-height: 1.6; }
.upload-dropzone { width: 100%; }
:deep(.upload-dropzone .el-upload-dragger) { width: 100%; padding: 34px 18px; border-radius: 16px; border: 1px dashed #d8cfbe; background: linear-gradient(180deg, #fffdfa 0%, #fff6ec 100%); }
.upload-dropzone__icon { margin-bottom: 10px; color: #b88f46; font-size: 28px; }
.upload-dropzone__title { color: #1c2e46; font-size: 16px; font-weight: 700; }
.upload-dropzone__desc { margin-top: 6px; color: #7e705c; font-size: 13px; }
.file-card,.behavior-placeholder,.guide-box,.result-strip,.result-summary,.error-box { border-radius: 20px; }
.file-card,.behavior-placeholder { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 16px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); }
.ghost-btn { min-height: 36px; padding: 0 14px; border-radius: 999px; border: 1px solid #dde3ef; background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%); color: #314661; font-size: 13px; font-weight: 700; cursor: pointer; }
.config-actions,.result-note,.side-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.config-tip { color: #70839d; font-size: 13px; }
.guide-box { display: grid; gap: 12px; padding: 16px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); }
.guide-box p { margin: 6px 0 0; color: #70839d; line-height: 1.7; }
.guide-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.guide-chips span { display: inline-flex; padding: 6px 10px; border-radius: 999px; background: #fff4e6; color: #87633e; font-size: 12px; font-weight: 700; }
.import-side { display: grid; gap: 16px; position: sticky; top: 18px; }
.side-card { padding: 18px; display: grid; gap: 14px; }
.side-card__summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.side-card__summary div { display: grid; gap: 4px; }
.side-card__summary small { color: #70839d; font-size: 12px; }
.side-card__summary strong,.side-card__head h3 { color: #1f2a44; font-size: 18px; }
.side-checks { display: grid; gap: 10px; }
.side-check { padding: 14px; border-radius: 18px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); }
.side-check--done { background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.4), transparent 55%), #fffdf6; border-color: #d8dfc7; }
.side-toggle { display: flex; justify-content: space-between; align-items: center; min-height: 38px; padding: 0 4px; background: transparent; border: 0; color: #36506f; font-weight: 700; cursor: pointer; }
.result-card,.history-card { padding: 24px; }
.result-strip { padding: 16px 18px; border: 1px dashed #d8cfbe; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); color: #70839d; line-height: 1.7; }
.result-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.result-summary { padding: 18px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); display: grid; gap: 8px; }
.result-summary span { color: #7e705c; font-size: 13px; }
.result-summary strong { font-size: 28px; }
.error-box { margin-top: 14px; display: grid; gap: 8px; padding: 16px; border: 1px solid #f2d7d7; background: #fff8f8; color: #8b4a4a; }
.history-card__meta { min-height: 34px; padding: 0 14px; border-radius: 999px; display: inline-flex; align-items: center; background: #fff4e6; border: 1px solid #ead7bc; color: #87633e; font-size: 13px; font-weight: 700; }
.history-table-shell { margin-top: 18px; overflow: hidden; border: 1.5px solid #e5ddd1; border-radius: 20px; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,0.84); }
.history-badge { min-height: 28px; padding: 0 10px; border-radius: 999px; display: inline-flex; align-items: center; background: linear-gradient(180deg, #fff4e6 0%, #f7ead6 100%); border: 1px solid #ead7bc; color: #87633e; font-size: 12px; font-weight: 700; }
.history-ok { color: #2f6e49; font-weight: 700; }
.history-errors { color: #8b4a4a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
:deep(.history-table-shell .el-table) { --el-table-border-color: #e8dfd3; --el-table-header-bg-color: #fbf4e8; --el-table-row-hover-bg-color: #fffaf2; background: transparent !important; }
:deep(.history-table-shell .el-table::before),
:deep(.history-table-shell .el-table--border::before),
:deep(.history-table-shell .el-table--border::after),
:deep(.history-table-shell .el-table__border-left-patch) { background: #e8dfd3 !important; }
:deep(.history-table-shell .el-table th.el-table__cell) { color: #7e705c; font-weight: 700; background: linear-gradient(180deg, #fcf6ec 0%, #f8efe2 100%) !important; }
:deep(.history-table-shell .el-table td.el-table__cell) { color: #1f3550; background: transparent !important; }
:deep(.history-table-shell .el-table tr td.el-table__cell),
:deep(.history-table-shell .el-table tr th.el-table__cell) { border-bottom: 1px solid #ece3d8 !important; }
:deep(.history-table-shell .el-table__row:nth-child(even) td.el-table__cell) { background: rgba(255, 250, 242, 0.72) !important; }
:deep(.history-table-shell .el-table__row:hover > td.el-table__cell) { background: linear-gradient(180deg, #fffaf2 0%, #fff6eb 100%) !important; }
:deep(.config-panel .el-select__wrapper) { min-height: 46px; border-radius: 16px !important; background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.92), 0 0 0 1px #e5ddd1 !important; }
:deep(.config-panel .el-select__wrapper.is-focused) { box-shadow: inset 0 1px 0 rgba(255,255,255,0.92), 0 0 0 1px rgba(184,143,70,0.42), 0 0 0 4px rgba(184,143,70,0.12) !important; }
:deep(.config-panel .el-select__selected-item),:deep(.config-panel .el-select__placeholder),:deep(.config-panel .el-select__caret) { color: #5f6f85 !important; }
:deep(.source-card .el-switch) { --el-switch-on-color: #9ac659; --el-switch-off-color: #d8d2c8; }
@media (max-width: 1200px) { .import-shell,.type-grid,.source-grid,.result-grid { grid-template-columns: 1fr; } .import-side { position: static; } }
@media (max-width: 900px) { .config-grid,.side-card__summary { grid-template-columns: 1fr; } .field-block--full { grid-column: span 1; } .import-main,.result-card,.history-card { padding: 20px; } }
</style>
