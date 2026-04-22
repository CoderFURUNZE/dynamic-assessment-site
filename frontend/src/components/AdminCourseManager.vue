<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HintButton from "./HintButton.vue";
import QueryToolbar from "./QueryToolbar.vue";

type Course = {
  id: number;
  code: string;
  title: string;
  description: string;
  active: boolean;
  lifecycle_status?: string;
  teacher_id?: number | null;
  teacher_name?: string;
  teacher_ids?: number[];
  teacher_names?: string[];
  teaching_teacher_count?: number;
  finished_teacher_count?: number;
  teaching_teacher_names?: string[];
  finished_teacher_names?: string[];
};

const loading = ref(false);
const courses = ref<Course[]>([]);
const teacherOptions = ref<Array<{ id: number; label: string }>>([]);
const togglingIds = ref<number[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);
const keyword = ref("");
const lifecycleFilter = ref("all");

const dialogOpen = ref(false);
const editing = ref<Course | null>(null);
const saving = ref(false);
const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
  active: true,
  lifecycle_status: "draft",
  teacher_ids: [] as number[],
});

const lifecycleOptions = [
  { label: "未开放", value: "draft" },
  { label: "开放中", value: "active" },
  { label: "已归档", value: "archived" },
];

function normalizeIsoMinute(value?: string | null) {
  if (!value) return "";
  return String(value).replace(" ", "T").slice(0, 16);
}

const isEdit = computed(() => Boolean(editing.value));
const filteredCourses = computed(() => {
  const q = keyword.value.trim().toLowerCase();
  return courses.value.filter((row) => {
    const matchesKeyword = !q || [row.code, row.title, row.description].join(" ").toLowerCase().includes(q);
    const matchesLifecycle = lifecycleFilter.value === "all" || String(row.lifecycle_status || "draft").toLowerCase() === lifecycleFilter.value;
    return matchesKeyword && matchesLifecycle;
  });
});
async function loadTeacherOptions() {
  const res = await api.get("/admin/users?page=1&page_size=500&role=teacher");
  const items = res.data.items ?? [];
  teacherOptions.value = items
    .filter((item: any) => item?.id)
    .map((item: any) => ({ id: Number(item.id), label: String(item.full_name || item.username || item.id) }));
}

async function load() {
  loading.value = true;
  try {
    const query = new URLSearchParams({ page: String(page.value), page_size: String(pageSize) });
    if (keyword.value.trim()) query.set("keyword", keyword.value.trim());
    const res = await api.get(`/admin/courses?${query.toString()}`);
    courses.value = res.data.items ?? [];
    total.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  editing.value = null;
  form.id = 0;
  form.code = "";
  form.title = "";
  form.description = "";
  form.active = true;
  form.lifecycle_status = "draft";
  form.teacher_ids = [];
  dialogOpen.value = true;
}

function openEdit(row: Course) {
  editing.value = row;
  form.id = row.id;
  form.code = row.code;
  form.title = row.title;
  form.description = row.description;
  form.active = row.active;
  form.lifecycle_status = row.lifecycle_status || (row.active ? "active" : "draft");
  form.teacher_ids = row.teacher_ids?.length ? [...row.teacher_ids] : row.teacher_id ? [row.teacher_id] : [];
  dialogOpen.value = true;
}

async function save() {
  if (saving.value) return;
  const payload = {
    code: form.code.trim(),
    title: form.title.trim(),
    description: form.description,
    active: form.active,
    lifecycle_status: form.lifecycle_status,
    teacher_ids: form.teacher_ids,
    teacher_id: form.teacher_ids[0] ?? null,
  };
  if (!payload.code || !payload.title) {
    ElMessage.warning("课程编码和课程名称不能为空");
    return;
  }
  saving.value = true;
  try {
    if (isEdit.value) {
      await api.put(`/admin/courses/${form.id}`, payload);
      ElMessage.success("课程已保存");
    } else {
      await api.post("/admin/courses", payload);
      ElMessage.success("课程已创建");
    }
    dialogOpen.value = false;
    await load();
  } catch (e: any) {
    const status = Number(e?.response?.status ?? 0);
    if (!status || status >= 500) {
      try {
        const probe = await api.get("/admin/courses", { params: { page: 1, page_size: 100, keyword: payload.code || payload.title } });
        const rows: Course[] = probe.data?.items ?? [];
        const matched = isEdit.value ? rows.find((row) => row.id === form.id) : rows.find((row) => row.code === payload.code && row.title === payload.title);
        if (matched && matched.code === payload.code && matched.title === payload.title) {
          ElMessage.success(isEdit.value ? "课程已保存（已自动确认）" : "课程已创建（已自动确认）");
          dialogOpen.value = false;
          await load();
          return;
        }
      } catch {}
    }
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  } finally {
    saving.value = false;
  }
}

async function remove(row: Course) {
  try {
    await api.delete(`/admin/courses/${row.id}`);
    ElMessage.success("课程已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败");
  }
}

function setCourseActiveLocal(courseId: number, active: boolean) {
  courses.value = courses.value.map((item) => (item.id === courseId ? { ...item, active } : item));
}
function isToggling(courseId: number) {
  return togglingIds.value.includes(courseId);
}
function enrollStatusLabel(value?: string) {
  const normalized = String(value || "open").toLowerCase();
  return enrollStatusOptions.find((item) => item.value === normalized)?.label ?? normalized;
}
function lifecycleLabel(value?: string) {
  const normalized = String(value || "draft").toLowerCase();
  return lifecycleOptions.find((item) => item.value === normalized)?.label || normalized;
}
function lifecycleClass(value?: string) {
  const normalized = String(value || "draft").toLowerCase();
  if (normalized === "active") return "is-active";
  if (normalized === "archived") return "is-archived";
  return "is-draft";
}
function enrollStatusClass(value?: string) {
  const normalized = String(value || "open").toLowerCase();
  if (normalized === "open") return "is-open";
  if (normalized === "full") return "is-full";
  if (normalized === "closed") return "is-closed";
  return "is-expired";
}
async function probeCourseActive(row: Course) {
  const probe = await api.get("/admin/courses", { params: { page: 1, page_size: 100, keyword: row.code || row.title || "" } });
  const rows: Course[] = probe.data?.items ?? [];
  return rows.find((item) => item.id === row.id) ?? null;
}
async function toggleActive(row: Course, value: boolean) {
  const previous = !value;
  if (isToggling(row.id)) return;
  togglingIds.value.push(row.id);
  try {
    const res = await api.put(`/admin/courses/${row.id}`, { active: value });
    const saved = Boolean(res?.data?.active ?? value);
    setCourseActiveLocal(row.id, saved);
    ElMessage.success(saved ? "课程已启用" : "课程已停用");
  } catch (e: any) {
    const status = Number(e?.response?.status ?? 0);
    if (!status || status >= 500) {
      try {
        const matched = await probeCourseActive(row);
        if (matched) {
          setCourseActiveLocal(row.id, Boolean(matched.active));
          if (Boolean(matched.active) === Boolean(value)) {
            ElMessage.success(value ? "课程已启用（已自动确认）" : "课程已停用（已自动确认）");
            return;
          }
        }
      } catch {}
    }
    setCourseActiveLocal(row.id, previous);
    ElMessage.error(e?.response?.data?.detail ?? "更新状态失败");
  } finally {
    togglingIds.value = togglingIds.value.filter((id) => id !== row.id);
  }
}

function searchCourses() {
  page.value = 1;
  load();
}

function resetSearch() {
  keyword.value = "";
  lifecycleFilter.value = "all";
  page.value = 1;
  load();
}

Promise.all([loadTeacherOptions(), load()]);
</script>

<template>
  <el-card class="panel-card course-manager-card" shadow="never">
    <div class="course-table-wrap">
      <div class="course-manager__table-header">
        <div class="course-manager__table-title-wrap">
          <div class="course-manager__table-title">课程列表</div>
          <div class="course-manager__table-controls">
            <div class="course-manager__table-query-group">
              <QueryToolbar
                v-model="keyword"
                placeholder="请输入课程名称或课程编码"
                hint="请输入课程名称或课程编码"
                input-width="420px"
                :show-reset="false"
                @search="searchCourses"
                @reset="resetSearch"
              />
              <HintButton class="course-manager__table-reset" @click="resetSearch">重置</HintButton>
            </div>
            <div class="course-manager__table-actions">
              <el-select v-model="lifecycleFilter" class="course-manager-filter" @change="searchCourses">
                <el-option label="全部状态" value="all" />
                <el-option v-for="item in lifecycleOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <HintButton @click="load" :loading="loading">刷新</HintButton>
              <HintButton type="primary" @click="openAdd">新增课程</HintButton>
            </div>
          </div>
        </div>
      </div>
        <el-table
          :data="filteredCourses"
          size="small"
          v-loading="loading"
          style="width: 100%"
          table-layout="fixed"
          border
        >
        <el-table-column prop="code" label="课程编码" width="140" />
        <el-table-column label="课程信息" min-width="240">
          <template #default="{ row }">
            <div class="course-cell">
              <strong>{{ row.title }}</strong>
              <span>{{ row.description || '暂未填写课程简介' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="教学设置" min-width="320">
          <template #default="{ row }">
            <div class="course-setting">
              <div class="course-setting__item course-setting__item--stack">
                <span class="course-setting__label">平台状态</span>
                <span class="course-setting__pill" :class="lifecycleClass(row.lifecycle_status)">{{ lifecycleLabel(row.lifecycle_status) }}</span>
              </div>
              <span class="course-setting__item">指定教师：{{ row.teacher_names?.length ? row.teacher_names.join('、') : (row.teacher_name || '暂未指定') }}</span>
              <span class="course-setting__item">
                教师授课：{{ row.teaching_teacher_count ?? 0 }} 位授课中，{{ row.finished_teacher_count ?? 0 }} 位已结课
              </span>
              <span v-if="(row.teaching_teacher_names?.length ?? 0) > 0" class="course-setting__item">
                授课教师：{{ row.teaching_teacher_names?.join('、') }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.active" :loading="isToggling(row.id)" @change="(v: boolean) => toggleActive(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <div class="course-row-actions">
              <HintButton size="small" @click="openEdit(row)">编辑</HintButton>
              <HintButton size="small" type="danger" @click="remove(row)">删除</HintButton>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="course-manager-pager">
      <el-pagination background layout="prev, pager, next" :page-size="pageSize" :total="total" v-model:current-page="page" @current-change="load" />
    </div>

    <el-dialog v-model="dialogOpen" :title="isEdit ? '编辑课程' : '新增课程'" width="680px">
      <el-form label-width="90px">
        <el-form-item label="课程编码"><el-input v-model="form.code" placeholder="唯一编码，学生可凭此加入" /></el-form-item>
        <el-form-item label="课程名称"><el-input v-model="form.title" placeholder="例如：数据结构" /></el-form-item>
        <el-form-item label="课程简介"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="平台状态">
          <el-select v-model="form.lifecycle_status" style="width: 100%">
            <el-option v-for="item in lifecycleOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="指定教师">
          <el-select
            v-model="form.teacher_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            :max-collapse-tags="3"
            clearable
            filterable
            placeholder="请选择授课教师"
            style="width: 100%"
          >
            <el-option v-for="item in teacherOptions" :key="item.id" :label="item.label" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.active" /></el-form-item>
      </el-form>
      <template #footer>
        <HintButton @click="dialogOpen = false">取消</HintButton>
        <HintButton type="primary" :loading="saving" @click="save">保存</HintButton>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.course-manager-card {
  min-width: 0;
  overflow: hidden;
  border: none;
  background: transparent;
  box-shadow: none;
}
.course-manager-card :deep(.el-card__body) {
  padding: 0;
  min-width: 0;
  overflow: hidden;
}
.course-manager-filter { width: 160px; }
.course-table-wrap {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 18px 20px 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  background: radial-gradient(circle at top right, rgba(219, 234, 254, 0.56), transparent 40%), #ffffff;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}
.course-manager__table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 2px 12px;
}
.course-manager__table-title-wrap {
  display: grid;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.course-manager__table-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.course-manager__table-query-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.course-manager__table-title {
  font-size: 18px;
  font-weight: 800;
  color: #1f3556;
}
.course-manager__table-title-wrap :deep(.query-toolbar) {
  flex: 1;
  width: 100%;
  max-width: 540px;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.course-manager__table-reset {
  display: inline-flex;
  flex: 0 0 auto;
}
.course-manager__table-reset :deep(.hint-button__inner) {
  min-width: 96px;
  min-height: 46px;
  padding-inline: 20px;
  border-radius: 18px;
  font-weight: 700;
}
.course-manager__table-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}
.course-manager__table-title-wrap :deep(.query-toolbar__row) {
  align-items: center;
}
.course-manager__table-actions :deep(.hint-button),
.course-manager__table-actions :deep(.el-select),
.course-manager__table-actions :deep(.el-select .el-select__wrapper) {
  min-height: 46px;
}
.course-table-wrap :deep(.el-table) {
  border-radius: 22px !important;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  box-shadow: none !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
  width: 100% !important;
  max-width: 100% !important;
}
.course-table-wrap :deep(.el-table__inner-wrapper) {
  border-radius: 22px !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
}
.course-table-wrap :deep(.el-table__header),
.course-table-wrap :deep(.el-table__body),
.course-table-wrap :deep(.el-table__footer) {
  width: 100% !important;
  table-layout: fixed !important;
}
.course-table-wrap :deep(.el-scrollbar),
.course-table-wrap :deep(.el-scrollbar__wrap),
.course-table-wrap :deep(.el-table__body-wrapper),
.course-table-wrap :deep(.el-table__header-wrapper) {
  width: 100% !important;
  max-width: 100% !important;
}
.course-table-wrap :deep(.el-table::before),
.course-table-wrap :deep(.el-table--border::before),
.course-table-wrap :deep(.el-table--border::after) {
  background: rgba(226, 232, 240, 0.9) !important;
}
.course-table-wrap :deep(.el-table__border-left-patch) {
  background: rgba(226, 232, 240, 0.9) !important;
}
.course-table-wrap :deep(.el-table th.el-table__cell) {
  background: #f8fafc !important;
  color: #475569;
  font-weight: 800;
}
.course-table-wrap :deep(.el-table td.el-table__cell),
.course-table-wrap :deep(.el-table th.el-table__cell) {
  padding-top: 16px;
  padding-bottom: 16px;
  border-right: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9) !important;
}
.course-table-wrap :deep(.el-table tr td:last-child),
.course-table-wrap :deep(.el-table tr th:last-child) {
  border-right: none !important;
}
.course-table-wrap :deep(.el-table__row:last-child td.el-table__cell) {
  border-bottom: none !important;
}
.course-table-wrap :deep(.el-table__row:hover > td.el-table__cell) {
  background: #f8fafc !important;
}
.course-table-wrap :deep(.el-switch) {
  --el-switch-on-color: #4a82ff;
  --el-switch-off-color: #d5e0ef;
}
.course-cell { display: grid; gap: 6px; }
.course-cell strong { color: #1f3556; font-size: 15px; }
.course-cell span,
.course-setting__item {
  color: #667d9b;
  line-height: 1.6;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.course-setting { display: grid; gap: 6px; }
.course-setting__item--stack {
  display: flex;
  align-items: center;
  gap: 8px;
}
.course-setting__label {
  color: #71839d;
}
.course-setting__pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.course-setting__pill.is-active,
.course-setting__pill.is-open {
  background: #dff6b6;
  color: #214f2f;
}
.course-setting__pill.is-draft {
  background: #dff2fb;
  color: #1f2937;
}
.course-setting__pill.is-archived,
.course-setting__pill.is-closed,
.course-setting__pill.is-expired {
  background: #f4f6f9;
  color: #7a889d;
}
.course-setting__pill.is-full {
  background: #fff4ea;
  color: #b56d2b;
}
.course-row-actions { display: flex; gap: 6px; }
.course-manager-pager { display: flex; justify-content: flex-end; margin-top: 12px; }
@media (max-width: 768px) {
  .course-manager-filter { width: 100%; }
  .course-manager__table-header { flex-direction: column; align-items: flex-start; }
  .course-manager__table-reset { width: 100%; }
  .course-manager__table-query-group,
  .course-manager__table-controls,
  .course-manager__table-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
  .course-manager__table-title-wrap :deep(.query-toolbar) {
    width: 100%;
    max-width: 100%;
  }
}
</style>
