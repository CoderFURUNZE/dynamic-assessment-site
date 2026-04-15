<template>
  <section class="panel-card stage-manager-card">
    <div class="stage-manager__table-wrap">
      <div class="stage-manager__header">
        <div class="stage-manager__title-wrap">
          <div class="stage-manager__title">阶段列表</div>
        </div>
        <div class="stage-manager__header-actions">
          <el-select
            :model-value="subject"
            size="small"
            class="stage-manager__course-select"
            placeholder="选择课程"
            @update:model-value="handleSubjectChange"
          >
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
          </el-select>
          <div class="stage-manager__total">共 {{ stages.length }} 条</div>
          <el-button class="da-outline-button stage-manager__toolbar-btn" @click="load">刷新</el-button>
          <el-button class="da-primary-button stage-manager__toolbar-btn" @click="openAdd">新增阶段</el-button>
        </div>
      </div>

      <el-empty
        v-if="!loading && !stages.length"
        class="stage-manager__empty"
        description="当前课程暂无阶段"
      />

      <el-table v-else :data="stages" v-loading="loading" border class="stage-manager__table">
        <el-table-column prop="stage_order" label="序号" width="90" />
        <el-table-column prop="title" label="阶段名称" min-width="240" />
        <el-table-column label="起止时间" min-width="220">
          <template #default="{ row }">
            {{ formatDate(row.starts_at) }} ~ {{ formatDate(row.ends_at) }}
          </template>
        </el-table-column>
        <el-table-column label="年级" width="110">
          <template #default>
            {{ grade || "通用" }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="300" show-overflow-tooltip />
        <el-table-column label="操作" width="190">
          <template #default="{ row }">
            <div class="stage-manager__row-actions">
              <el-button class="da-outline-button stage-manager__action-btn" @click="openEdit(row)">编辑</el-button>
              <el-button class="da-danger-button stage-manager__action-btn" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogOpen"
      :title="editingId ? '编辑阶段' : '新增阶段'"
      width="560px"
      destroy-on-close
    >
      <el-form label-width="92px">
        <el-form-item label="阶段名称">
          <el-input v-model="form.title" placeholder="请输入阶段名称" />
        </el-form-item>
        <el-form-item label="阶段序号">
          <el-input-number v-model="form.stage_order" :min="1" controls-position="right" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.starts_at" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.ends_at" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入阶段说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="da-outline-button" @click="dialogOpen = false">取消</el-button>
        <el-button class="da-primary-button" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

type Stage = {
  id: number;
  title: string;
  stage_order: number;
  starts_at: string;
  ends_at: string;
  description: string;
};

const props = defineProps<{
  courseId: number | null;
  subject: string;
  grade: string;
  courses: Array<{ id: number; title: string; code?: string }>;
}>();

const emit = defineEmits<{
  (e: "stage-changed"): void;
  (e: "subject-change", value: string): void;
}>();

const loading = ref(false);
const stages = ref<Stage[]>([]);
const dialogOpen = ref(false);
const editingId = ref<number | null>(null);

const form = reactive({
  title: "",
  stage_order: 1,
  starts_at: "",
  ends_at: "",
  description: "",
});

function formatDate(value: string) {
  return value || "--";
}

function resetForm() {
  editingId.value = null;
  form.title = "";
  form.stage_order = 1;
  form.starts_at = "";
  form.ends_at = "";
  form.description = "";
}

function handleSubjectChange(value: string) {
  emit("subject-change", value);
}

async function load() {
  if (!props.courseId) {
    stages.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await api.get(`/stages/courses/${props.courseId}`);
    stages.value = data ?? [];
  } catch (error: any) {
    stages.value = [];
    ElMessage.error(error?.response?.data?.detail ?? "加载阶段列表失败");
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  resetForm();
  dialogOpen.value = true;
}

function openEdit(row: Stage) {
  editingId.value = row.id;
  form.title = row.title;
  form.stage_order = row.stage_order;
  form.starts_at = row.starts_at;
  form.ends_at = row.ends_at;
  form.description = row.description || "";
  dialogOpen.value = true;
}

async function save() {
  if (!props.courseId) return;
  const payload = {
    course_id: props.courseId,
    subject: props.subject,
    grade: props.grade,
    title: form.title,
    stage_order: form.stage_order,
    starts_at: form.starts_at,
    ends_at: form.ends_at,
    description: form.description,
  };
  try {
    if (editingId.value) {
      await api.put(`/stages/${editingId.value}`, payload);
      ElMessage.success("阶段已更新");
    } else {
      await api.post(`/stages/courses/${props.courseId}`, payload);
      ElMessage.success("阶段已新增");
    }
    dialogOpen.value = false;
    await load();
    window.dispatchEvent(new CustomEvent("da:teacher-stage-changed", { detail: { courseId: props.courseId } }));
    emit("stage-changed");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "保存阶段失败");
  }
}

async function remove(row: Stage) {
  try {
    await ElMessageBox.confirm(`确认删除阶段“${row.title}”吗？`, "提示", { type: "warning" });
    await api.delete(`/stages/${row.id}`);
    ElMessage.success("阶段已删除");
    await load();
    window.dispatchEvent(new CustomEvent("da:teacher-stage-changed", { detail: { courseId: props.courseId } }));
    emit("stage-changed");
  } catch (error: any) {
    if (error === "cancel" || error === "close") return;
    if (error?.response?.data?.detail) {
      ElMessage.error(error.response.data.detail);
    }
  }
}

watch(
  () => props.courseId,
  async () => {
    dialogOpen.value = false;
    resetForm();
    await load();
  },
  { immediate: true },
);

onMounted(load);
</script>

<style scoped>
.stage-manager-card {
  min-width: 0;
  overflow: hidden;
  border: none;
  background: transparent;
  box-shadow: none;
}

.stage-manager__table-wrap {
  position: relative;
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 22px 20px 22px;
  border: 2px solid #1f2937;
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(210, 238, 255, 0.44), transparent 34%),
    radial-gradient(circle at left center, rgba(255, 255, 255, 0.72), transparent 36%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 10px 0 rgba(31, 41, 55, 0.1);
}

.stage-manager__table-wrap::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 88px;
  background: linear-gradient(180deg, rgba(215, 249, 168, 0.12), rgba(255, 255, 255, 0));
  pointer-events: none;
}

.stage-manager__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 2px 18px;
  margin-bottom: 2px;
  position: relative;
  z-index: 1;
}

.stage-manager__title-wrap {
  display: grid;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.stage-manager__title {
  font-size: 20px;
  font-weight: 800;
  color: #17325c;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.stage-manager__subtitle {
  font-size: 13px;
  line-height: 1.6;
  color: var(--app-text-soft);
}

.stage-manager__header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.stage-manager__total {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f5fbe8 0%, #eef8d9 100%);
  border: 1px solid #cfe7a8;
  color: #355a28;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.stage-manager__course-select {
  width: 384px;
  max-width: 100%;
}

.stage-manager__header-actions :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 16px !important;
  background: linear-gradient(180deg, #fffdfb 0%, #fff7ee 100%) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 1px #d8dfef !important;
}

.stage-manager__header-actions :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 1px rgba(104, 142, 202, 0.52),
    0 0 0 4px rgba(104, 142, 202, 0.12),
    0 14px 28px rgba(86, 111, 148, 0.08) !important;
}

.stage-manager__header-actions :deep(.el-select__placeholder),
.stage-manager__header-actions :deep(.el-select__selected-item),
.stage-manager__header-actions :deep(.el-select__caret) {
  color: #5f6f85 !important;
}

.stage-manager__toolbar-btn {
  min-height: 44px;
  padding-inline: 20px;
  border-radius: 16px;
  font-weight: 700;
  transition:
    transform var(--app-duration) var(--app-ease-out),
    box-shadow var(--app-duration) var(--app-ease-out),
    border-color var(--app-duration) var(--app-ease-out),
    background var(--app-duration) var(--app-ease-out);
}

.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn) {
  margin-left: 0;
  border-width: 1px;
}

.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn:hover) {
  transform: translateY(-1px);
}

.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn.da-outline-button) {
  border-color: #d6dfef;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  color: #29476a;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn.da-outline-button:hover),
.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn.da-outline-button:focus-visible) {
  border-color: #c8d5eb;
  background: linear-gradient(180deg, #fffefb 0%, #f8fbf1 100%);
  color: #1f4f95;
}

.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn.da-primary-button) {
  border-color: #c7e38e;
  background: linear-gradient(180deg, #edf9cf 0%, #dff2b4 100%);
  color: #23421f;
  box-shadow: 0 10px 18px rgba(182, 214, 118, 0.26);
}

.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn.da-primary-button:hover),
.stage-manager__header-actions :deep(.el-button.stage-manager__toolbar-btn.da-primary-button:focus-visible) {
  box-shadow: 0 14px 24px rgba(182, 214, 118, 0.34);
}

.stage-manager__empty {
  padding: 36px 0 24px;
}

.stage-manager__row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.stage-manager__action-btn {
  flex: 0 0 auto;
  min-width: 0;
  min-height: 36px;
  padding: 0 15px;
  border-radius: 999px;
  font-weight: 700;
  box-shadow: none;
  transition:
    transform var(--app-duration) var(--app-ease-out),
    background var(--app-duration) var(--app-ease-out),
    border-color var(--app-duration) var(--app-ease-out);
}

.stage-manager__row-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn) {
  border-width: 1px;
}

.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn.da-outline-button) {
  background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%);
  border-color: #d6dfef;
  color: #1f4f95;
}

.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn.da-outline-button:hover),
.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn.da-outline-button:focus-visible) {
  background: linear-gradient(180deg, #fffefb 0%, #f7fbf0 100%);
  border-color: #c8d5eb;
  color: #173f79;
  transform: translateY(-1px);
}

.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn.da-danger-button) {
  background: linear-gradient(180deg, #ffffff 0%, #fff8f8 100%);
  border-color: rgba(239, 91, 99, 0.24);
  color: #dc5f66;
}

.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn.da-danger-button:hover),
.stage-manager__row-actions :deep(.el-button.stage-manager__action-btn.da-danger-button:focus-visible) {
  background: linear-gradient(180deg, #fffdfd 0%, #fff1f2 100%);
  border-color: rgba(239, 91, 99, 0.34);
  color: #cf4d56;
  transform: translateY(-1px);
}

.stage-manager__table-wrap :deep(.el-table) {
  border-radius: 24px !important;
  overflow: hidden;
  border: 1px solid #d9e3f2 !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.88) !important;
  background: linear-gradient(180deg, #fffdfa 0%, #fffaf4 100%) !important;
  width: 100% !important;
  max-width: 100% !important;
  margin-top: 2px;
}

.stage-manager__table-wrap :deep(.el-table__inner-wrapper) {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  border-radius: 24px !important;
}

.stage-manager__table-wrap :deep(.el-table__header),
.stage-manager__table-wrap :deep(.el-table__body),
.stage-manager__table-wrap :deep(.el-table__footer) {
  width: 100% !important;
  table-layout: fixed !important;
}

.stage-manager__table-wrap :deep(.el-scrollbar),
.stage-manager__table-wrap :deep(.el-scrollbar__wrap),
.stage-manager__table-wrap :deep(.el-table__body-wrapper),
.stage-manager__table-wrap :deep(.el-table__header-wrapper) {
  width: 100% !important;
  max-width: 100% !important;
}

.stage-manager__table-wrap :deep(.el-table__fixed),
.stage-manager__table-wrap :deep(.el-table__fixed-right) {
  box-shadow: none !important;
}

.stage-manager__table-wrap :deep(.el-table::before),
.stage-manager__table-wrap :deep(.el-table--border::before),
.stage-manager__table-wrap :deep(.el-table--border::after),
.stage-manager__table-wrap :deep(.el-table__border-left-patch) {
  background: #dde6f2 !important;
}

.stage-manager__table-wrap :deep(.el-table th.el-table__cell) {
  background:
    linear-gradient(180deg, rgba(246, 250, 232, 0.92) 0%, rgba(251, 252, 244, 0.92) 100%) !important;
  color: #17325c;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.stage-manager__table-wrap :deep(.el-table td.el-table__cell),
.stage-manager__table-wrap :deep(.el-table th.el-table__cell) {
  padding-top: 17px;
  padding-bottom: 17px;
  border-right: 1px solid rgba(229, 234, 241, 0.9) !important;
  border-bottom: 1px solid rgba(229, 234, 241, 0.9) !important;
}

.stage-manager__table-wrap :deep(.el-table tr td:last-child),
.stage-manager__table-wrap :deep(.el-table tr th:last-child) {
  border-right: none !important;
}

.stage-manager__table-wrap :deep(.el-table__row:last-child td.el-table__cell) {
  border-bottom: none !important;
}

.stage-manager__table-wrap :deep(.el-table__body tr:nth-child(even) > td.el-table__cell) {
  background: rgba(255, 251, 245, 0.92) !important;
}

.stage-manager__table-wrap :deep(.el-table__row:hover > td.el-table__cell) {
  background: linear-gradient(180deg, #f8fbef 0%, #f2f8e2 100%) !important;
}

.stage-manager__table-wrap :deep(.el-table .cell) {
  color: #274263;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.7;
}

.stage-manager__table-wrap :deep(.el-table__row .el-table__cell:first-child .cell) {
  font-weight: 700;
  color: #5d7595;
}

.stage-manager__table-wrap :deep(.el-table__row .el-table__cell:nth-child(2) .cell) {
  font-weight: 700;
  color: #1f4678;
}

.stage-manager__table-wrap :deep(.el-table__row .el-table__cell:nth-child(4) .cell) {
  font-weight: 700;
  color: #355a28;
}

@media (max-width: 900px) {
  .stage-manager__header {
    flex-direction: column;
    align-items: flex-start;
  }

  .stage-manager__header-actions {
    width: 100%;
    align-self: stretch;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .stage-manager__table-wrap {
    padding: 18px 16px 18px;
    border-radius: 24px;
  }

  .stage-manager__total {
    margin-right: 0;
  }

  .stage-manager__course-select {
    width: 100%;
  }

  .stage-manager__toolbar-btn {
    min-width: 108px;
  }
}
</style>
