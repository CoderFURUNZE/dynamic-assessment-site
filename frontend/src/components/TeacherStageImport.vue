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
  columns: string[];
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
const workspaceCards = [
  { key: "AUTO", title: "一键导入系统数据", desc: "自动汇总站内学习与行为数据，快速生成阶段初始画像。" },
  { key: "FILE", title: "上传整班文件", desc: "补录线下考勤、课堂参与、展示表现等教师整理数据。" },
  { key: "CHECK", title: "预览并复核结果", desc: "导入后查看成功率、失败原因和影响学生数，再进入画像页。" },
];

const canUpload = computed(() => Boolean(props.courseId && selectedStageId.value && uploadFile.value));
const selectedGuide = computed(() => metricGuides.value.find((item) => item.metric_type === metricType.value) ?? null);
const selectedStageLabel = computed(() => stages.value.find((item) => item.id === selectedStageId.value)?.title || "未选择阶段");
const enabledSystemMappings = computed(() => [systemMappings.video, systemMappings.practice, systemMappings.mastery, systemMappings.behavior].filter(Boolean).length);
const latestBatchIds = computed(() => lastResult.value?.import_summary?.batch_ids ?? []);
const latestSourceLabels = computed(() => {
  const sourceMap: Record<string, string> = { video: "视频学习", practice: "练习表现", mastery: "掌握度", behavior: "行为信号" };
  return (lastResult.value?.import_summary?.enabled_sources ?? []).map((item) => sourceMap[item] ?? item);
});
const qualityLabel = computed(() => {
  const status = lastResult.value?.import_summary?.quality_status;
  if (status === "excellent") return "优秀";
  if (status === "warning") return "需复核";
  if (status === "risk") return "存在风险";
  return "待生成";
});
const resultSummary = computed(() => {
  if (!lastResult.value) return null;
  return {
    recalculationScope: lastResult.value.import_summary?.recalculation_scope ?? `已重算 ${lastResult.value.recalculated_users ?? 0} 名学生的阶段画像`,
    qualityHint: lastResult.value.import_summary?.quality_hint ?? (lastResult.value.failed_rows === 0 ? "本次导入没有失败记录，可直接查看画像结果。" : "存在失败记录，建议先根据错误提示修正后再补导。"),
  };
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
    if (!props.courseId) { stages.value = []; batches.value = []; internalSummary.value = null; return; }
    await loadStages();
    await loadBatches();
    await loadInternalSummary();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载阶段导入数据失败");
  } finally { loading.value = false; }
}
function handleExternalStageChange(event: Event) {
  const custom = event as CustomEvent<{ courseId?: number | null }>;
  const changedCourseId = Number(custom.detail?.courseId || 0);
  if (props.courseId && (!changedCourseId || changedCourseId === Number(props.courseId))) refresh().catch((e: any) => ElMessage.error(e?.response?.data?.detail ?? "同步阶段数据失败"));
}
function onFileChange(file: any) { uploadFile.value = file?.raw ?? null; }
async function upload() {
  if (!canUpload.value || !props.courseId || !selectedStageId.value || !uploadFile.value) return ElMessage.warning("请先选择阶段并上传导入文件");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("metric_type", metricType.value);
  form.append("file", uploadFile.value);
  try {
    const data = (await api.post("/stages/imports/upload", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data; uploadFile.value = null; importView.value = "preview";
    ElMessage.success(`导入完成：成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条，已重算 ${data.recalculated_users ?? 0} 名学生`);
    await loadBatches();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "文件导入失败"); }
}
function openProfiles() { emit("view-profiles"); }
async function downloadTemplate() {
  try {
    const res = await api.get(`/stages/template?metric_type=${encodeURIComponent(metricType.value)}`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = `stage_template_${metricType.value}.csv`; link.click(); window.URL.revokeObjectURL(url);
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "下载模板失败"); }
}
async function downloadInternalSummary() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  try {
    const res = await api.get(`/stages/internal-summary/export?course_id=${props.courseId}&stage_id=${selectedStageId.value}`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = `internal_stage_summary_${props.courseId}_${selectedStageId.value}.csv`; link.click(); window.URL.revokeObjectURL(url);
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "导出系统汇总失败"); }
}
async function applyInternalSummary() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  if (!enabledSystemMappings.value) return ElMessage.warning("请至少选择一个系统汇总来源");
  const form = new FormData();
  form.append("course_id", String(props.courseId));
  form.append("stage_id", String(selectedStageId.value));
  form.append("include_video", String(systemMappings.video));
  form.append("include_practice", String(systemMappings.practice));
  form.append("include_mastery", String(systemMappings.mastery));
  try {
    const data = (await api.post("/stages/internal-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    lastResult.value = data; importView.value = "preview";
    ElMessage.success(`系统汇总已应用：生成 ${data.success_rows} 条阶段记录，已重算 ${data.recalculated_users ?? 0} 名学生`);
    await loadBatches(); await loadInternalSummary();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "应用系统汇总失败"); }
}
async function applyOneClickImport() {
  if (!props.courseId || !selectedStageId.value) return ElMessage.warning("请先选择课程和阶段");
  if (!enabledSystemMappings.value) return ElMessage.warning("请至少选择一个系统汇总来源");
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
    lastResult.value = data; importView.value = "preview";
    ElMessage.success(`一键导入完成：生成 ${data.success_rows} 条记录，已重算 ${data.recalculated_users ?? 0} 名学生`);
    await loadBatches(); await loadInternalSummary();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail ?? "一键导入失败"); }
  finally { oneClickApplying.value = false; }
}

watch(() => props.courseId, () => { uploadFile.value = null; refresh(); }, { immediate: true });
watch(selectedStageId, () => {
  loadBatches().catch((e: any) => ElMessage.error(e?.response?.data?.detail ?? "加载导入历史失败"));
  loadInternalSummary().catch((e: any) => ElMessage.error(e?.response?.data?.detail ?? "加载系统汇总失败"));
});
onMounted(() => { window.addEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener); });
onBeforeUnmount(() => { window.removeEventListener("da:teacher-stage-changed", handleExternalStageChange as EventListener); });
</script>

<template>
  <el-card class="panel-card" shadow="never" v-loading="loading">
    <template #header>
      <div class="import-header">
        <div>
          <div class="import-title">阶段数据导入</div>
          <div class="import-subtitle">把系统汇总数据、行为信号和整班文件统一收口到当前阶段，作为动态评价与画像生成的输入。</div>
        </div>
        <div class="import-actions">
          <HintButton size="small" tip="刷新阶段、系统汇总和导入历史" :loading="loading" @click="refresh">刷新</HintButton>
          <HintButton size="small" tip="下载当前数据类型的导入模板" @click="downloadTemplate">下载模板</HintButton>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId" description="请先在顶部选择课程" />
    <template v-else>
      <div class="import-overview">
        <div class="import-overview__card"><span>当前课程</span><strong>{{ subject || "未选择课程" }}</strong><small>先选阶段，再导入对应阶段的整班数据。</small></div>
        <div class="import-overview__card"><span>当前阶段</span><strong>{{ selectedStageLabel }}</strong><small>同一阶段可以累计系统汇总和教师补录数据。</small></div>
        <div class="import-overview__card"><span>最近重算人数</span><strong>{{ lastResult?.recalculated_users ?? 0 }}</strong><small>显示最近一次导入后被重新计算画像的学生数。</small></div>
      </div>
      <div class="workspace-strip">
        <article v-for="card in workspaceCards" :key="card.key" class="workspace-strip__card"><span class="workspace-strip__badge">{{ card.key }}</span><strong>{{ card.title }}</strong><p>{{ card.desc }}</p></article>
      </div>
      <el-tabs v-model="importView" class="import-view-tabs" stretch>
        <el-tab-pane label="导入配置与上传" name="import" />
        <el-tab-pane label="预览与结果复核" name="preview" />
        <el-tab-pane label="导入历史" name="history" />
      </el-tabs>
      <el-alert v-if="importView === 'import'" type="info" :closable="false" show-icon class="import-view-help"><template #title>推荐操作顺序</template><div>先选择阶段，再决定是使用“一键导入系统数据”还是“上传整班文件”，导入完成后到结果页检查成功率和错误信息。</div></el-alert>
      <el-alert v-else-if="importView === 'preview'" type="info" :closable="false" show-icon class="import-view-help"><template #title>结果复核说明</template><div>这里用于查看系统汇总预览、最近一次导入结果以及失败原因。建议先复核，再进入学生画像页查看变化。</div></el-alert>
      <el-alert v-else type="info" :closable="false" show-icon class="import-view-help"><template #title>导入历史说明</template><div>按时间追踪每一次批量导入的成功率、失败记录和文件来源，便于教师排查问题和补导数据。</div></el-alert>

      <div class="import-grid" :style="{ gridTemplateColumns: importView === 'import' ? 'minmax(320px, 420px) 1fr' : '1fr' }">
        <section class="import-panel" v-if="importView === 'import'">
          <div class="import-auto-card">
            <div class="panel-mini-title">一键导入系统数据</div>
            <div class="import-auto-card__text">系统会按当前课程和阶段自动汇总站内学习数据，包括视频学习、练习表现、掌握度变化和行为信号，适合作为阶段初始画像。</div>
            <div class="mapping-panel">
              <div class="mapping-panel__title">系统来源选择</div>
              <div class="mapping-list">
                <label class="mapping-item"><el-switch v-model="systemMappings.video" /><div class="mapping-item__body"><strong>视频学习数据</strong><span>写入观看分钟数和平均完成率，反映学习投入程度。</span></div></label>
                <label class="mapping-item"><el-switch v-model="systemMappings.practice" /><div class="mapping-item__body"><strong>练习表现数据</strong><span>写入练习次数、正确率和完成情况，反映过程质量。</span></div></label>
                <label class="mapping-item"><el-switch v-model="systemMappings.mastery" /><div class="mapping-item__body"><strong>掌握度与推荐推进</strong><span>写入掌握度、问卷更新和推荐推进记录，反映阶段进展。</span></div></label>
                <label class="mapping-item"><el-switch v-model="systemMappings.behavior" /><div class="mapping-item__body"><strong>行为信号</strong><span>导入系统自动采集的行为事件和注意力信号，补充动态评价依据。</span></div></label>
              </div>
              <div class="mapping-panel__hint">当前已选 {{ enabledSystemMappings }} 个来源。一键导入会把这些来源统一写入当前阶段，并重新计算阶段画像。</div>
            </div>
            <div class="import-auto-card__actions">
              <HintButton tip="重新加载当前阶段的系统汇总预览" @click="loadInternalSummary">刷新系统数据</HintButton>
              <HintButton tip="导出当前阶段的系统汇总 CSV" @click="downloadInternalSummary">导出系统汇总 CSV</HintButton>
              <HintButton type="primary" :loading="oneClickApplying" tip="统一导入系统汇总和行为信号，并自动重算画像" @click="applyOneClickImport">一键导入全部来源</HintButton>
              <HintButton type="primary" tip="只应用系统汇总，不包含行为信号" @click="applyInternalSummary">仅应用系统汇总</HintButton>
            </div>
            <div v-if="internalSummary" class="import-auto-card__stats">
              <div class="import-auto-card__stat"><span>学生总数</span><strong>{{ internalSummary.summary.student_count }}</strong></div>
              <div class="import-auto-card__stat"><span>有视频数据</span><strong>{{ internalSummary.summary.video_students }}</strong></div>
              <div class="import-auto-card__stat"><span>有练习数据</span><strong>{{ internalSummary.summary.practice_students }}</strong></div>
              <div class="import-auto-card__stat"><span>有推荐推进</span><strong>{{ internalSummary.summary.recommendation_students }}</strong></div>
            </div>
          </div>

          <div class="panel-mini-title">上传整班阶段文件</div>
          <div class="import-tip-inline"><span>导入说明</span><HoverTip content="先选阶段，再选数据类型，下载模板后按字段填写，再上传 CSV 或 XLSX。导入成功后系统会批量重算当前阶段画像。" /></div>
          <el-form label-width="110px">
            <el-form-item label="课程"><el-input :model-value="subject || '未选择课程'" disabled /></el-form-item>
            <el-form-item label="阶段"><el-select v-model="selectedStageId" style="width: 100%" placeholder="选择阶段"><el-option v-for="item in stages" :key="item.id" :label="`${item.stage_order}. ${item.title}`" :value="item.id" /></el-select></el-form-item>
            <el-form-item label="数据类型"><el-select v-model="metricType" style="width: 100%"><el-option v-for="item in metricOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="上传文件"><el-upload :auto-upload="false" :show-file-list="true" :limit="1" @change="onFileChange"><el-button>选择整班 CSV / XLSX</el-button></el-upload></el-form-item>
            <el-form-item><HintButton type="primary" :disabled="!canUpload" tip="按当前阶段批量导入整班文件并重算画像" @click="upload">上传并生成阶段画像</HintButton></el-form-item>
          </el-form>
          <div class="import-hint">推荐先下载模板再填写，至少保证 `username` 或 `student_no` 能匹配到学生账号。</div>
          <div class="import-hint import-hint--merge">教师手工上传的线下考勤、课堂参与、展示表现等补充数据，会与系统自动汇总结果共同保留在当前阶段并再次触发重算。</div>
          <TeacherBehaviorImport :course-id="courseId" :stage-id="selectedStageId" :subject="subject" :grade="grade" :stage-title="selectedStageLabel" />
        </section>
        <section class="import-panel import-panel--history">
          <template v-if="importView === 'preview'">
            <div v-if="internalSummary" class="guide-panel">
              <div class="panel-mini-title">系统汇总预览</div>
              <div class="guide-summary">这是当前阶段内系统已经自动采集到的数据，可先用来复核系统数据覆盖范围，再决定是否补充导入线下数据。</div>
              <el-table :data="internalSummary.rows.slice(0, 8)" size="small" style="width: 100%">
                <el-table-column prop="username" label="账号" width="120" />
                <el-table-column prop="student_no" label="学号" width="120" />
                <el-table-column prop="watched_minutes" label="视频分钟" width="110" />
                <el-table-column label="练习正确率" width="120"><template #default="{ row }">{{ Math.round((row.practice_accuracy || 0) * 100) }}%</template></el-table-column>
                <el-table-column prop="practice_attempts" label="练习次数" width="100" />
                <el-table-column label="掌握度" width="100"><template #default="{ row }">{{ Math.round((row.course_mastery || 0) * 100) }}%</template></el-table-column>
                <el-table-column label="动态评价" width="100"><template #default="{ row }">{{ Math.round((row.dynamic_score || 0) * 100) }}%</template></el-table-column>
                <el-table-column prop="risk_level" label="风险等级" min-width="120" />
              </el-table>
            </div>

            <div v-if="lastResult" class="import-result-card">
              <div class="result-brief">
                <div class="result-brief__item"><span>当前阶段</span><strong>{{ lastResult.import_summary?.stage_title || selectedStageLabel }}</strong></div>
                <div class="result-brief__item"><span>质量状态</span><strong>{{ qualityLabel }}</strong></div>
                <div class="result-brief__item"><span>导入来源</span><strong>{{ latestSourceLabels.length ? latestSourceLabels.join(" / ") : "手工文件导入" }}</strong></div>
              </div>
              <div class="panel-mini-title">最近一次导入结果</div>
              <div class="import-result-card__metrics">
                <div class="import-result-card__metric"><span>总记录数</span><strong>{{ lastResult.total_rows }}</strong></div>
                <div class="import-result-card__metric"><span>成功导入</span><strong>{{ lastResult.success_rows }}</strong></div>
                <div class="import-result-card__metric"><span>失败记录</span><strong>{{ lastResult.failed_rows }}</strong></div>
                <div class="import-result-card__metric"><span>重算学生</span><strong>{{ lastResult.recalculated_users }}</strong></div>
              </div>
              <div v-if="resultSummary" class="result-explain">
                <div class="result-explain__line"><span>重算范围</span><strong>{{ resultSummary.recalculationScope }}</strong></div>
                <div class="result-explain__line"><span>质量说明</span><strong>{{ resultSummary.qualityHint }}</strong></div>
                <div v-if="latestBatchIds.length" class="result-explain__line"><span>关联批次</span><strong>#{{ latestBatchIds.join(" / #") }}</strong></div>
              </div>
              <div class="import-result-card__next">{{ lastResult.next_action || "导入完成后，可直接进入学生画像页查看本次阶段重算结果。" }}</div>
              <div class="import-result-card__actions"><HintButton type="primary" tip="跳转到学生画像页查看本次导入结果" @click="openProfiles">查看学生画像</HintButton></div>
              <div v-if="lastResult.errors?.length" class="error-stack"><div v-for="item in lastResult.errors.slice(0, 5)" :key="item">{{ item }}</div></div>
            </div>

            <div v-if="selectedGuide" class="guide-panel">
              <div class="panel-mini-title">当前数据类型说明</div>
              <div class="guide-summary">{{ selectedGuide.summary }}</div>
              <div class="guide-block"><div class="guide-label">模板字段</div><div class="guide-chips"><span v-for="item in selectedGuide.template_fields" :key="item" class="guide-chip">{{ item }}</span></div></div>
              <div class="guide-block"><div class="guide-label">影响的一维指标</div><div class="guide-chips"><span v-for="item in selectedGuide.affected_dimensions" :key="item" class="guide-chip guide-chip--blue">{{ item }}</span></div></div>
              <div class="guide-block"><div class="guide-label">重点影响指标</div><div class="guide-chips"><span v-for="item in selectedGuide.affected_indicators" :key="item" class="guide-chip guide-chip--soft">{{ item }}</span></div></div>
              <div class="guide-next">{{ selectedGuide.next_action }}</div>
            </div>
          </template>
          <template v-else>
            <div class="panel-mini-title">导入历史</div>
            <el-table :data="batches" size="small" style="width: 100%">
              <el-table-column prop="created_at" label="时间" width="180"><template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 19) }}</template></el-table-column>
              <el-table-column prop="stage_title" label="阶段" min-width="180" />
              <el-table-column prop="metric_type" label="类型" width="120" />
              <el-table-column prop="file_name" label="文件" min-width="180" />
              <el-table-column label="成功/总数" width="140"><template #default="{ row }"><span>{{ row.success_rows }}/{{ row.total_rows }}</span></template></el-table-column>
              <el-table-column label="错误预览" min-width="240"><template #default="{ row }"><div v-if="row.error_preview.length === 0" class="ok-text">无</div><div v-else class="error-stack"><div v-for="item in row.error_preview" :key="item">{{ item }}</div></div></template></el-table-column>
            </el-table>
          </template>
        </section>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.import-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.import-title { font-size: 18px; font-weight: 700; color: var(--app-ink); }
.import-subtitle { margin-top: 4px; color: #64748b; line-height: 1.6; }
.import-actions,.import-auto-card__actions,.import-result-card__actions { display: flex; gap: 8px; flex-wrap: wrap; }
.import-overview,.workspace-strip { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; margin-bottom: 16px; }
.import-overview__card,.workspace-strip__card,.import-auto-card__stat,.import-result-card__metric,.result-brief__item,.result-explain__line { padding: 16px 18px; border-radius: 18px; border: 1px solid #dfe9f2; background: #fff; display: grid; gap: 6px; }
.import-overview__card span,.import-auto-card__stat span,.import-result-card__metric span,.result-brief__item span,.result-explain__line span { font-size: 12px; color: #7a8ca2; }
.import-overview__card strong,.import-auto-card__stat strong,.import-result-card__metric strong,.result-brief__item strong,.result-explain__line strong { font-size: 22px; color: #243854; line-height: 1.5; }
.import-overview__card small,.import-auto-card__text,.guide-summary,.guide-next,.import-result-card__next,.mapping-panel__hint,.import-hint { color: #5f7591; line-height: 1.7; }
.workspace-strip__card { background: linear-gradient(180deg,#fff 0%,#f4f8fc 100%); }
.workspace-strip__badge { width: fit-content; padding: 4px 8px; border-radius: 999px; background: #e8f1ff; color: #315b95; font-size: 11px; font-weight: 700; }
.workspace-strip__card strong { color: #243854; font-size: 15px; }
.workspace-strip__card p { margin: 0; color: #64748b; line-height: 1.6; font-size: 13px; }
.import-view-help { margin-bottom: 16px; }
.import-grid { display: grid; grid-template-columns: minmax(320px,420px) 1fr; gap: 16px; }
.import-panel { padding: 18px; border-radius: 20px; border: 1px solid #dfe9f2; background: linear-gradient(180deg,#fbfdff,#f6f9fc); }
.panel-mini-title { font-size: 16px; font-weight: 700; color: var(--app-ink); margin-bottom: 14px; }
.import-auto-card,.guide-panel,.import-result-card { margin-bottom: 18px; padding: 16px; border-radius: 18px; border: 1px solid #d7e6fb; background: linear-gradient(180deg,#f9fbff 0%,#f3f7ff 100%); display: grid; gap: 12px; }
.mapping-panel { padding: 14px; border-radius: 16px; border: 1px solid #d9e4f3; background: rgba(255,255,255,.82); display: grid; gap: 12px; }
.mapping-panel__title,.guide-label { font-size: 13px; font-weight: 700; color: #243854; }
.mapping-list,.guide-block,.result-explain { display: grid; gap: 10px; }
.mapping-item { display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: start; padding: 12px; border-radius: 14px; border: 1px solid #e1eaf1; background: #fff; }
.mapping-item__body { display: grid; gap: 4px; }
.mapping-item__body strong { font-size: 13px; color: #243854; }
.mapping-item__body span { color: #627790; line-height: 1.6; font-size: 12px; }
.import-auto-card__stats,.import-result-card__metrics { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px; }
.result-brief { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 10px; }
.guide-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.guide-chip { padding: 6px 10px; border-radius: 999px; border: 1px solid #dfe9f2; background: #f5f8fc; color: #5d7390; font-size: 12px; line-height: 1; }
.guide-chip--blue { background: #eef5ff; border-color: #cfe0fb; color: #476da8; }
.guide-chip--soft { background: #f7faff; }
.import-tip-inline { display: flex; align-items: center; gap: 8px; color: #627790; margin-bottom: 12px; font-size: 13px; }
.import-hint--merge { padding: 12px 14px; border-radius: 14px; background: #f8fbff; border: 1px dashed #cfe0fb; margin-top: 8px; margin-bottom: 12px; }
.ok-text { color: #4b9c68; }
.error-stack { display: grid; gap: 4px; color: #c45b54; font-size: 12px; line-height: 1.5; }
@media (max-width: 1100px) { .import-overview,.workspace-strip,.import-grid { grid-template-columns: 1fr; } .import-auto-card__stats,.import-result-card__metrics,.result-brief { grid-template-columns: repeat(2,minmax(0,1fr)); } }
</style>
