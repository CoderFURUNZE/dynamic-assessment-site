<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

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

const props = defineProps<{
  courseId: number | null;
  subject: string;
  grade: string;
}>();

const loading = ref(false);
const stages = ref<Stage[]>([]);
const batches = ref<ImportBatch[]>([]);
const selectedStageId = ref<number | null>(null);
const metricType = ref("video");
const uploadFile = ref<File | null>(null);

const metricOptions = [
  { label: "视频学习记录", value: "video" },
  { label: "作业完成记录", value: "assignment" },
  { label: "小测成绩记录", value: "quiz" },
  { label: "考勤记录", value: "attendance" },
  { label: "任务完成记录", value: "task" },
  { label: "课堂参与记录", value: "participation" },
];

const canUpload = computed(() => Boolean(props.courseId && selectedStageId.value && uploadFile.value));

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

async function refresh() {
  if (!props.courseId) {
    stages.value = [];
    batches.value = [];
    return;
  }
  loading.value = true;
  try {
    await loadStages();
    await loadBatches();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载导入数据失败");
  } finally {
    loading.value = false;
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
    ElMessage.success(`导入完成：成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条`);
    uploadFile.value = null;
    await loadBatches();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导入失败");
  }
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
});
</script>

<template>
  <el-card class="panel-card" shadow="never" v-loading="loading">
    <template #header>
      <div class="import-header">
        <div>
          <div class="import-title">阶段数据导入</div>
          <div class="import-subtitle">按阶段上传视频、作业、小测、考勤或任务数据，作为后续画像与动态评价的输入来源。</div>
        </div>
        <div class="import-actions">
          <el-button size="small" @click="refresh" :loading="loading">刷新</el-button>
          <el-button size="small" @click="downloadTemplate">下载模板</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId" description="请先在顶部选择课程" />

    <template v-else>
      <div class="import-grid">
        <section class="import-panel">
          <div class="panel-mini-title">导入配置</div>
          <el-form label-width="110px">
            <el-form-item label="课程">
              <el-input :model-value="subject || '未选择课程'" disabled />
            </el-form-item>
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
                <el-button>选择 CSV / XLSX</el-button>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canUpload" @click="upload">开始导入</el-button>
            </el-form-item>
          </el-form>
          <div class="import-hint">
            当前支持按模板导入阶段数据。建议先下载模板，再按示例字段填充，至少保证 `username` 或 `student_no` 能匹配到学生。
          </div>
        </section>

        <section class="import-panel import-panel--history">
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

.import-hint {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: #eef5fb;
  color: #4f6c89;
  font-size: 13px;
  line-height: 1.6;
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
  .import-grid {
    grid-template-columns: 1fr;
  }
}
</style>
