<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";
import HintButton from "./HintButton.vue";
import TeacherBehaviorImport from "./TeacherBehaviorImport.vue";

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
  batch_id: number;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  recalculated_users: number;
  next_action: string;
  errors: string[];
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
type ImportView = "import" | "preview" | "history";

const props = defineProps<{ courseId: number | null; subject: string; grade: string }>();
const emit = defineEmits<{ (e: "view-profiles"): void }>();

const loading = ref(false);
const stages = ref<Stage[]>([]);
const batches = ref<ImportBatch[]>([]);
const metricGuides = ref<MetricGuide[]>([]);
const selectedStageId = ref<number | null>(null);
const metricType = ref("video");
const uploadFile = ref<File | null>(null);
const lastResult = ref<ImportResult | null>(null);
const internalSummary = ref<InternalSummary | null>(null);
const oneClickApplying = ref(false);
const importView = ref<ImportView>("import");
const systemMappings = reactive({ video: true, practice: true, mastery: true, behavior: true });

const metricOptions = [
  { label: "视频学习记录", value: "video" },
  { label: "作业完成记录", value: "assignment" },
  { label: "小测成绩记录", value: "quiz" },
  { label: "考勤记录", value: "attendance" },
  { label: "任务完成记录", value: "task" },
  { label: "课堂参与记录", value: "participation" },
];

const selectedStageLabel = computed(() => stages.value.find((item) => item.id === selectedStageId.value)?.title || "未选择阶段");
const selectedGuide = computed(() => metricGuides.value.find((item) => item.metric_type === metricType.value) ?? null);
const canUpload = computed(() => Boolean(props.courseId && selectedStageId.value && uploadFile.value));
const enabledSystemMappings = computed(() => [systemMappings.video, systemMappings.practice, systemMappings.mastery, systemMappings.behavior].filter(Boolean).length);
const summaryRows = computed(() => internalSummary.value?.rows.slice(0, 8) ?? []);
const recentBatches = computed(() => batches.value.slice(0, 5));
const latestBatchIds = computed(() => lastResult.value?.import_summary?.batch_ids ?? []);
const completionRate = computed(() => {
  if (!lastResult.value || !lastResult.value.total_rows) return "0%";
  return `${Math.round((lastResult.value.success_rows / lastResult.value.total_rows) * 100)}%`;
});
const qualityLabel = computed(() => {
  const value = lastResult.value?.import_summary?.quality_status;
  if (value === "excellent") return "优秀";
  if (value === "warning") return "需复核";
  if (value === "risk") return "存在风险";
  return "待生成";
});
const sourceLabels = computed(() => {
  const sourceMap: Record<string, string> = {
    video: "视频学习",
    practice: "练习表现",
    mastery: "掌握度变化",
    behavior: "行为信号",
  };
  return (lastResult.value?.import_summary?.enabled_sources ?? []).map((item) => sourceMap[item] ?? item);
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
  if (!stages.value.some((item) => item.id === selectedStageId.value)) {
    selectedStageId.value = stages.value[0]?.id ?? null;
  }
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
    ElMessage.error(e?.response?.data?.detail ?? "加载阶段导入数据失败");
  } finally {
    loading.value = false;
  }
}

function onFileChange(file: any) {
  uploadFile.value = file?.raw ?? null;
}

async function upload() {
  if (!canUpload.value || !props.courseId || !selectedStageId.value || !uploadFile.value) {
    return ElMessage.warning("请先选择阶段并上传导入文件");
  }
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("metric_type", metricType.value);
  form.append("file", uploadFile.value);
  try {
    const data = (await api.post("/stages/imports/upload", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data;
    uploadFile.value = null;
    importView.value = "preview";
    await loadBatches();
    ElMessage.success(`导入完成：成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条，已重算 ${data.recalculated_users ?? 0} 名学生`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "文件导入失败");
  }
}

async function applyInternalSummary() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("include_video", String(systemMappings.video));
  form.append("include_practice", String(systemMappings.practice));
  form.append("include_mastery", String(systemMappings.mastery));
  try {
    const data = (await api.post("/stages/internal-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data;
    importView.value = "preview";
    await loadBatches();
    await loadInternalSummary();
    ElMessage.success(`系统汇总已应用：生成 ${data.success_rows} 条阶段记录，已重算 ${data.recalculated_users ?? 0} 名学生`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "应用系统汇总失败");
  }
}

async function applyOneClickImport() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("include_video", String(systemMappings.video));
  form.append("include_practice", String(systemMappings.practice));
  form.append("include_mastery", String(systemMappings.mastery));
  form.append("include_behavior", String(systemMappings.behavior));
  oneClickApplying.value = true;
  try {
    const data = (await api.post("/stages/one-click-import", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data;
    importView.value = "preview";
    await loadBatches();
    await loadInternalSummary();
    ElMessage.success(`一键导入完成：生成 ${data.success_rows} 条记录，已重算 ${data.recalculated_users ?? 0} 名学生`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "一键导入失败");
  } finally {
    oneClickApplying.value = false;
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
    ElMessage.error(e?.response?.data?.detail ?? "下载模板失败");
  }
}

async function downloadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
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
    ElMessage.error(e?.response?.data?.detail ?? "导出系统汇总失败");
  }
}

function openProfiles() {
  emit("view-profiles");
}

function handleExternalStageChange(event: Event) {
  const custom = event as CustomEvent<{ courseId?: number | null }>;
  const changedCourseId = Number(custom.detail?.courseId || 0);
  if (props.courseId && (!changedCourseId || changedCourseId === Number(props.courseId))) {
    refresh().catch((e: any) => ElMessage.error(e?.response?.data?.detail ?? "同步阶段数据失败"));
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
  <el-card class="stage-import" shadow="never" v-loading="loading">
    <template #header>
      <div class="stage-import__header">
        <div class="stage-import__intro">
          <span class="stage-import__eyebrow">阶段导入</span>
          <div class="stage-import__title">阶段导入工作台</div>
          <p class="stage-import__subtitle">把系统汇总、整班补录和结果复核压缩进一套连续工作流里，页面重点放在清楚、顺手、稳定。</p>
        </div>
        <div class="stage-import__toolbar">
          <HintButton size="small" :loading="loading" tip="刷新阶段、预览和导入历史" @click="refresh">刷新</HintButton>
          <HintButton size="small" tip="下载当前数据类型的导入模板" @click="downloadTemplate">下载模板</HintButton>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId" description="请先在顶部选择课程" />
    <template v-else>
      <section class="stage-import__hero">
        <div class="hero-copy">
          <h2>先选阶段，再导入，再复核</h2>
          <p>左侧只放操作，右侧只放状态和结果，不再把所有卡片都堆在一列里，避免视觉重心失衡。</p>
        </div>
        <div class="hero-stats">
          <div class="stat-card"><span>当前课程</span><strong>{{ subject || "未选择课程" }}</strong></div>
          <div class="stat-card"><span>当前阶段</span><strong>{{ selectedStageLabel }}</strong></div>
          <div class="stat-card"><span>最近重算</span><strong>{{ lastResult?.recalculated_users ?? 0 }}</strong></div>
          <div class="stat-card"><span>最近成功率</span><strong>{{ completionRate }}</strong></div>
        </div>
      </section>

      <el-tabs v-model="importView" class="stage-import__tabs">
        <el-tab-pane label="导入配置" name="import" />
        <el-tab-pane label="结果复核" name="preview" />
        <el-tab-pane label="导入历史" name="history" />
      </el-tabs>

      <div class="stage-import__layout">
        <main class="stage-import__main">
          <section class="panel-card">
            <div class="panel-card__title">当前导入范围</div>
            <div class="scope-grid">
              <div class="scope-item">
                <span>课程</span>
                <strong>{{ subject || "未选择课程" }}</strong>
                <small>只会写入当前选中课程的阶段数据。</small>
              </div>
              <div class="scope-item">
                <span>阶段</span>
                <strong>{{ selectedStageLabel }}</strong>
                <small>系统汇总和教师补录都会归并到这个阶段。</small>
              </div>
              <div class="scope-item">
                <span>最近批次</span>
                <strong>{{ latestBatchIds.length ? `#${latestBatchIds[0]}` : "暂无" }}</strong>
                <small>用于追踪本次导入记录。</small>
              </div>
            </div>
          </section>

          <template v-if="importView === 'import'">
            <div class="import-columns">
              <section class="panel-card">
                <div class="panel-card__header">
                  <div>
                    <div class="panel-card__eyebrow">系统汇总</div>
                    <div class="panel-card__title">系统汇总导入</div>
                  </div>
                  <HintButton size="small" tip="导出当前阶段系统汇总 CSV" @click="downloadInternalSummary">导出汇总</HintButton>
                </div>
                <p class="panel-card__desc">优先导入系统已经采集到的视频、练习、掌握度和行为信号，用于快速生成阶段初始画像。</p>
                <div class="mapping-grid">
                  <label class="mapping-item">
                    <el-switch v-model="systemMappings.video" />
                    <div><strong>视频学习</strong><span>观看分钟与平均完成率</span></div>
                  </label>
                  <label class="mapping-item">
                    <el-switch v-model="systemMappings.practice" />
                    <div><strong>练习表现</strong><span>练习次数、正确率、完成情况</span></div>
                  </label>
                  <label class="mapping-item">
                    <el-switch v-model="systemMappings.mastery" />
                    <div><strong>掌握度变化</strong><span>掌握度、问卷更新、推荐推进</span></div>
                  </label>
                  <label class="mapping-item">
                    <el-switch v-model="systemMappings.behavior" />
                    <div><strong>行为信号</strong><span>行为事件与注意力信号</span></div>
                  </label>
                </div>
                <div class="panel-card__hint">当前已选 {{ enabledSystemMappings }} 个来源。一键导入会统一写入当前阶段并重新计算画像。</div>
                <div class="panel-card__actions">
                  <HintButton type="primary" tip="只应用系统汇总，不包含行为信号" @click="applyInternalSummary">仅应用系统汇总</HintButton>
                  <HintButton type="primary" :loading="oneClickApplying" tip="统一导入系统汇总和行为信号" @click="applyOneClickImport">一键导入全部来源</HintButton>
                </div>
                <div v-if="internalSummary" class="mini-stats">
                  <div class="mini-stat"><span>学生</span><strong>{{ internalSummary.summary.student_count }}</strong></div>
                  <div class="mini-stat"><span>视频覆盖</span><strong>{{ internalSummary.summary.video_students }}</strong></div>
                  <div class="mini-stat"><span>练习覆盖</span><strong>{{ internalSummary.summary.practice_students }}</strong></div>
                  <div class="mini-stat"><span>推荐推进</span><strong>{{ internalSummary.summary.recommendation_students }}</strong></div>
                </div>
              </section>

              <section class="panel-card">
                <div class="panel-card__header">
                  <div>
                    <div class="panel-card__eyebrow">文件补录</div>
                    <div class="panel-card__title">整班文件补录</div>
                  </div>
                  <div class="inline-tip">
                    <span>导入说明</span>
                    <HoverTip content="先选阶段，再选数据类型，下载模板后按字段填写，再上传 CSV 或 XLSX。导入成功后系统会批量重算当前阶段画像。" />
                  </div>
                </div>
                <el-form label-width="90px">
                  <el-form-item label="阶段">
                    <el-select v-model="selectedStageId" style="width: 100%" placeholder="选择阶段">
                      <el-option v-for="item in stages" :key="item.id" :label="`${item.stage_order}. ${item.title}`" :value="item.id" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="数据类型">
                    <el-select v-model="metricType" style="width: 100%">
                      <el-option v-for="item in metricOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="上传文件">
                    <el-upload :auto-upload="false" :show-file-list="true" :limit="1" @change="onFileChange">
                      <el-button>选择整班 CSV / XLSX</el-button>
                    </el-upload>
                  </el-form-item>
                  <el-form-item>
                    <HintButton type="primary" :disabled="!canUpload" tip="按当前阶段批量导入整班文件并重算画像" @click="upload">上传并生成阶段画像</HintButton>
                  </el-form-item>
                </el-form>
                <div class="note-grid">
                  <div class="note-card"><strong>模板匹配</strong><span>建议至少保证 `username` 或 `student_no` 能匹配到学生账号。</span></div>
                  <div class="note-card"><strong>合并方式</strong><span>教师补录会与系统汇总结果共同保留在当前阶段。</span></div>
                </div>
              </section>
            </div>

            <TeacherBehaviorImport
              :course-id="courseId"
              :stage-id="selectedStageId"
              :subject="subject"
              :grade="grade"
              :stage-title="selectedStageLabel"
            />
          </template>

          <template v-else-if="importView === 'preview'">
            <section class="panel-card" v-if="internalSummary">
              <div class="panel-card__title">系统汇总预览</div>
              <el-table :data="summaryRows" size="small" style="width: 100%">
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
                <el-table-column label="动态评价" width="100">
                  <template #default="{ row }">{{ Math.round((row.dynamic_score || 0) * 100) }}%</template>
                </el-table-column>
                <el-table-column prop="risk_level" label="风险等级" min-width="120" />
              </el-table>
            </section>

            <section class="panel-card" v-if="lastResult">
              <div class="panel-card__header">
                <div class="panel-card__title">最近一次导入结果</div>
                <HintButton type="primary" tip="跳转到学生画像页查看本次导入结果" @click="openProfiles">查看学生画像</HintButton>
              </div>
              <div class="mini-stats">
                <div class="mini-stat"><span>总记录数</span><strong>{{ lastResult.total_rows }}</strong></div>
                <div class="mini-stat"><span>成功导入</span><strong>{{ lastResult.success_rows }}</strong></div>
                <div class="mini-stat"><span>失败记录</span><strong>{{ lastResult.failed_rows }}</strong></div>
                <div class="mini-stat"><span>质量状态</span><strong>{{ qualityLabel }}</strong></div>
              </div>
              <div class="note-grid note-grid--wide">
                <div class="note-card"><strong>导入来源</strong><span>{{ sourceLabels.length ? sourceLabels.join(" / ") : "手工文件导入" }}</span></div>
                <div class="note-card"><strong>重算范围</strong><span>{{ lastResult.import_summary?.recalculation_scope || `已重算 ${lastResult.recalculated_users} 名学生` }}</span></div>
                <div class="note-card"><strong>质量说明</strong><span>{{ lastResult.import_summary?.quality_hint || lastResult.next_action }}</span></div>
              </div>
              <div v-if="lastResult.errors?.length" class="error-stack">
                <div v-for="item in lastResult.errors.slice(0, 5)" :key="item">{{ item }}</div>
              </div>
            </section>

            <section class="panel-card" v-if="selectedGuide">
              <div class="panel-card__title">当前数据类型说明</div>
              <p class="panel-card__desc">{{ selectedGuide.summary }}</p>
              <div class="note-grid note-grid--wide">
                <div class="note-card"><strong>模板字段</strong><span>{{ selectedGuide.template_fields.join("、") }}</span></div>
                <div class="note-card"><strong>影响的维度</strong><span>{{ selectedGuide.affected_dimensions.join("、") }}</span></div>
                <div class="note-card"><strong>重点影响指标</strong><span>{{ selectedGuide.affected_indicators.join("、") }}</span></div>
              </div>
            </section>
          </template>

          <template v-else>
            <section class="panel-card">
              <div class="panel-card__title">导入历史与错误复盘</div>
              <el-table :data="batches" size="small" style="width: 100%">
                <el-table-column prop="created_at" label="时间" width="180">
                  <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 19) }}</template>
                </el-table-column>
                <el-table-column prop="stage_title" label="阶段" min-width="180" />
                <el-table-column prop="metric_type" label="类型" width="120" />
                <el-table-column prop="file_name" label="文件" min-width="180" />
                <el-table-column label="成功/总数" width="140">
                  <template #default="{ row }">{{ row.success_rows }}/{{ row.total_rows }}</template>
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
          </template>
        </main>

        <aside class="stage-import__side">
          <section class="panel-card panel-card--sticky">
            <div class="panel-card__title">导入建议</div>
            <ol class="checklist">
              <li>先确认课程和阶段，再执行导入，避免不同阶段的数据混写。</li>
              <li>优先导入系统汇总，再决定是否补录教师线下文件。</li>
              <li>导入完成后先看结果复核，再进入学生分析页查看动态变化。</li>
            </ol>
          </section>

          <section class="panel-card panel-card--sticky">
            <div class="panel-card__title">当前快照</div>
            <div class="mini-stats mini-stats--side">
              <div class="mini-stat"><span>阶段数</span><strong>{{ stages.length }}</strong></div>
              <div class="mini-stat"><span>历史批次</span><strong>{{ batches.length }}</strong></div>
              <div class="mini-stat"><span>系统预览行</span><strong>{{ internalSummary?.rows.length ?? 0 }}</strong></div>
            </div>
          </section>

          <section class="panel-card panel-card--sticky" v-if="recentBatches.length">
            <div class="panel-card__title">最近导入记录</div>
            <div class="history-list">
              <div v-for="item in recentBatches" :key="item.id" class="history-item">
                <div class="history-item__head">
                  <strong>{{ item.stage_title }}</strong>
                  <span>{{ item.metric_type }}</span>
                </div>
                <small>{{ item.created_at.replace("T", " ").slice(0, 16) }}</small>
                <p>成功 {{ item.success_rows }}/{{ item.total_rows }}，失败 {{ item.failed_rows }}</p>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.stage-import {
  border-radius: 28px;
  border: 1px solid #dfe7f2;
  background: radial-gradient(circle at top right, rgba(74, 115, 184, 0.12), transparent 22%), linear-gradient(180deg, #fff 0%, #f6f9ff 100%);
  box-shadow: 0 24px 56px rgba(30, 52, 86, 0.08);
}

.stage-import__header,
.stage-import__toolbar,
.stage-import__hero,
.hero-stats,
.scope-grid,
.import-columns,
.mapping-grid,
.mini-stats,
.note-grid,
.stage-import__layout,
.panel-card__header,
.inline-tip {
  display: flex;
  gap: 16px;
}

.stage-import__header,
.panel-card__header {
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
}

.stage-import__intro,
.hero-copy,
.workflow-card,
.panel-card,
.stat-card,
.scope-item,
.mapping-item,
.mini-stat,
.note-card,
.history-item {
  display: grid;
  gap: 8px;
}

.stage-import__eyebrow,
.panel-card__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #4a73b8;
}

.stage-import__title {
  font-size: 24px;
  font-weight: 800;
  color: #20344f;
}

.stage-import__subtitle,
.hero-copy p,
.panel-card__desc,
.panel-card__hint,
.mapping-item span,
.note-card span,
.history-item small,
.history-item p,
.scope-item small {
  color: #61758f;
  line-height: 1.75;
}

.stage-import__subtitle {
  margin: 8px 0 0;
  max-width: 760px;
}

.stage-import__hero {
  align-items: stretch;
  justify-content: space-between;
  padding: 24px;
  margin-bottom: 18px;
  border-radius: 24px;
  border: 1px solid #d9e4f4;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(236, 244, 255, 0.98));
}

.hero-copy {
  flex: 1 1 360px;
}

.hero-copy h2 {
  margin: 0 0 8px;
  font-size: 28px;
  line-height: 1.2;
  color: #20344f;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(170px, 1fr));
  flex: 0 1 420px;
}

.stat-card,
.scope-item,
.mini-stat,
.note-card {
  padding: 15px 16px;
  border-radius: 18px;
  border: 1px solid #dfe7f2;
  background: #f9fbff;
}

.stat-card span,
.scope-item span,
.mini-stat span {
  font-size: 12px;
  color: #7488a0;
}

.stat-card strong,
.scope-item strong,
.mini-stat strong {
  font-size: 22px;
  line-height: 1.4;
  color: #20344f;
}

.stage-import__tabs {
  margin-bottom: 18px;
}

.stage-import__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
}

.stage-import__main,
.stage-import__side,
.history-list {
  display: grid;
  gap: 18px;
}

.panel-card {
  padding: 20px;
  border-radius: 24px;
  border: 1px solid #dfe7f2;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 28px rgba(29, 53, 87, 0.05);
}

.panel-card__title {
  font-size: 18px;
  font-weight: 800;
  color: #20344f;
}

.panel-card--sticky {
  position: sticky;
  top: 16px;
}

.scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.import-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
}

.mapping-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.mapping-item {
  grid-template-columns: auto 1fr;
  align-items: start;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid #dfe7f2;
  background: #f9fbff;
}

.mapping-item strong,
.note-card strong,
.history-item__head strong {
  color: #20344f;
}

.panel-card__actions,
.stage-import__toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.mini-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.mini-stats--side {
  grid-template-columns: 1fr;
}

.note-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.note-grid--wide {
  grid-template-columns: 1fr;
}

.inline-tip {
  align-items: center;
  color: #61758f;
  font-size: 13px;
}

.checklist {
  margin: 0;
  padding-left: 18px;
  color: #556a83;
  line-height: 1.85;
}

.history-item {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid #dfe7f2;
  background: #f9fbff;
}

.history-item__head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.history-item__head span {
  padding: 4px 10px;
  border-radius: 999px;
  background: #eaf2ff;
  color: #4069ac;
  font-size: 11px;
  font-weight: 800;
}

.history-item p {
  margin: 0;
}

.error-stack {
  display: grid;
  gap: 6px;
  color: #c45b54;
  font-size: 12px;
  line-height: 1.6;
}

.ok-text {
  color: #4d9b6b;
}

@media (max-width: 1280px) {
  .stage-import__layout,
  .scope-grid,
  .import-columns,
  .mapping-grid,
  .mini-stats,
  .note-grid {
    grid-template-columns: 1fr;
  }

  .stage-import__hero {
    flex-direction: column;
  }

  .hero-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel-card--sticky {
    position: static;
  }
}

@media (max-width: 768px) {
  .hero-copy h2 {
    font-size: 22px;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }

  .stat-card strong,
  .scope-item strong,
  .mini-stat strong {
    font-size: 18px;
  }
}
</style>
