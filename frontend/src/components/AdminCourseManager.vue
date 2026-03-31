<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HintButton from "./HintButton.vue";

type Course = {
  id: number;
  code: string;
  title: string;
  description: string;
  active: boolean;
  lifecycle_status?: string;
  target_class?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  teacher_id?: number | null;
  max_students?: number;
  apply_deadline?: string | null;
  enroll_status?: string;
};

type Teacher = {
  id: number;
  username: string;
  full_name: string;
  role: string;
};

const loading = ref(false);
const courses = ref<Course[]>([]);
const teachers = ref<Teacher[]>([]);
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
  target_class: "",
  start_at: "",
  end_at: "",
  teacher_id: null as number | null,
  max_students: 200,
  apply_deadline: "",
  enroll_status: "open",
});

const lifecycleOptions = [
  { label: "待开课", value: "draft" },
  { label: "开课中", value: "active" },
  { label: "已归档", value: "archived" },
];

const enrollStatusOptions = [
  { label: "开放报名", value: "open" },
  { label: "名额已满", value: "full" },
  { label: "关闭报名", value: "closed" },
  { label: "已截止", value: "expired" },
];

function normalizeIsoMinute(value?: string | null) {
  if (!value) return "";
  return String(value).replace(" ", "T").slice(0, 16);
}

const isEdit = computed(() => Boolean(editing.value));
const teacherNameMap = computed(() => {
  const map = new Map<number, string>();
  for (const item of teachers.value) map.set(item.id, item.full_name || item.username);
  return map;
});
const filteredCourses = computed(() => {
  const q = keyword.value.trim().toLowerCase();
  return courses.value.filter((row) => {
    const matchesKeyword = !q || [row.code, row.title, row.description, teacherNameMap.value.get(row.teacher_id || 0) || ""].join(" ").toLowerCase().includes(q);
    const matchesLifecycle = lifecycleFilter.value === "all" || String(row.lifecycle_status || "draft").toLowerCase() === lifecycleFilter.value;
    return matchesKeyword && matchesLifecycle;
  });
});
const courseStats = computed(() => ({
  active: courses.value.filter((item) => String(item.lifecycle_status || "draft").toLowerCase() === "active").length,
  draft: courses.value.filter((item) => String(item.lifecycle_status || "draft").toLowerCase() === "draft").length,
  archived: courses.value.filter((item) => String(item.lifecycle_status || "draft").toLowerCase() === "archived").length,
}));

async function loadTeachers() {
  const res = await api.get("/admin/users?page=1&page_size=200");
  teachers.value = (res.data.items ?? []).filter((item: Teacher) => item.role === "teacher");
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
  form.target_class = "";
  form.start_at = "";
  form.end_at = "";
  form.teacher_id = null;
  form.max_students = 200;
  form.apply_deadline = "";
  form.enroll_status = "open";
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
  form.target_class = row.target_class || "";
  form.start_at = row.start_at ? row.start_at.slice(0, 16) : "";
  form.end_at = row.end_at ? row.end_at.slice(0, 16) : "";
  form.teacher_id = row.teacher_id ?? null;
  form.max_students = Number(row.max_students ?? 200);
  form.apply_deadline = row.apply_deadline ? row.apply_deadline.slice(0, 16) : "";
  form.enroll_status = row.enroll_status || "open";
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
    target_class: form.target_class.trim() || null,
    start_at: form.start_at ? new Date(form.start_at).toISOString() : null,
    end_at: form.end_at ? new Date(form.end_at).toISOString() : null,
    teacher_id: form.teacher_id,
    max_students: Math.max(1, Number(form.max_students || 1)),
    apply_deadline: form.apply_deadline ? new Date(form.apply_deadline).toISOString() : null,
    enroll_status: form.enroll_status,
  };
  if (!payload.code || !payload.title) {
    ElMessage.warning("课程编码和课程名称不能为空");
    return;
  }
  saving.value = true;
  try {
    if (isEdit.value) {
      await api.put(`/admin/courses/${form.id}`, payload);
      ElMessage.success("已更新课程");
    } else {
      await api.post("/admin/courses", payload);
      ElMessage.success("已新增课程");
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
        if (matched && matched.code === payload.code && matched.title === payload.title && normalizeIsoMinute(matched.apply_deadline) === normalizeIsoMinute(payload.apply_deadline)) {
          ElMessage.success(isEdit.value ? "已更新课程（已自动确认）" : "已新增课程（已自动确认）");
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
    ElMessage.success("已删除");
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

Promise.all([loadTeachers(), load()]);
</script>

<template>
  <el-card class="panel-card course-manager-card" shadow="never">
    <template #header>
      <div class="course-manager-header">
        <div class="course-manager-header__main">
          <div class="course-manager-header__eyebrow">Course Admin</div>
          <div class="course-manager-header__title">课程列表与配置</div>
          <div class="course-manager-header__desc">先筛选和定位课程，再进行编辑、启停和报名配置。</div>
        </div>
        <div class="course-manager-header__actions">
          <el-input v-model="keyword" placeholder="搜索课程名称 / 编码 / 教师" class="course-manager-search" clearable />
          <el-select v-model="lifecycleFilter" class="course-manager-filter">
            <el-option label="全部状态" value="all" />
            <el-option v-for="item in lifecycleOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <HintButton @click="load" :loading="loading">刷新</HintButton>
          <HintButton type="primary" @click="openAdd">新增课程</HintButton>
        </div>
      </div>
    </template>

    <div class="course-manager-stats">
      <span>开课中 {{ courseStats.active }}</span>
      <span>待开课 {{ courseStats.draft }}</span>
      <span>已归档 {{ courseStats.archived }}</span>
      <span>筛选后 {{ filteredCourses.length }}</span>
    </div>

    <div class="course-table-wrap">
      <el-table :data="filteredCourses" size="small" v-loading="loading" style="width: 100%">
        <el-table-column prop="code" label="课程编码" width="140" />
        <el-table-column label="课程信息" min-width="240">
          <template #default="{ row }">
            <div class="course-cell">
              <strong>{{ row.title }}</strong>
              <span>{{ row.description || '暂无课程简介' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="教学设置" min-width="260">
          <template #default="{ row }">
            <div class="course-setting">
              <span class="course-setting__item">状态：{{ lifecycleLabel(row.lifecycle_status) }}</span>
              <span class="course-setting__item">班级：{{ row.target_class || '未设置' }}</span>
              <span class="course-setting__item">教师：{{ row.teacher_id ? teacherNameMap.get(row.teacher_id) || `教师#${row.teacher_id}` : '未激活' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="报名设置" min-width="220">
          <template #default="{ row }">
            <div class="course-setting">
              <span class="course-setting__item">名额：{{ row.max_students ?? 200 }}</span>
              <span class="course-setting__item">状态：{{ enrollStatusLabel(row.enroll_status) }}</span>
              <span class="course-setting__item">截止：{{ row.apply_deadline ? row.apply_deadline.replace('T', ' ').slice(0, 16) : '未设置' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.active" :loading="isToggling(row.id)" @change="(v: boolean) => toggleActive(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
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

    <el-dialog v-model="dialogOpen" :title="isEdit ? '编辑课程' : '新增课程'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="课程编码"><el-input v-model="form.code" placeholder="唯一编码，学生可凭此加入" /></el-form-item>
        <el-form-item label="课程名称"><el-input v-model="form.title" placeholder="例如：数据结构" /></el-form-item>
        <el-form-item label="激活教师">
          <el-select v-model="form.teacher_id" clearable placeholder="不指定，等待教师自己激活" style="width: 100%">
            <el-option v-for="teacher in teachers" :key="teacher.id" :label="teacher.full_name || teacher.username" :value="teacher.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程简介"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="开课状态">
          <el-select v-model="form.lifecycle_status" style="width: 100%">
            <el-option v-for="item in lifecycleOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标班级"><el-input v-model="form.target_class" placeholder="例如 计科221" /></el-form-item>
        <el-form-item label="开始时间"><el-date-picker v-model="form.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm" format="YYYY-MM-DD HH:mm" placeholder="课程开始时间" style="width: 100%" /></el-form-item>
        <el-form-item label="结束时间"><el-date-picker v-model="form.end_at" type="datetime" value-format="YYYY-MM-DDTHH:mm" format="YYYY-MM-DD HH:mm" placeholder="课程结束时间" style="width: 100%" /></el-form-item>
        <el-form-item label="课程名额"><el-input-number v-model="form.max_students" :min="1" :max="9999" style="width: 100%" /></el-form-item>
        <el-form-item label="报名截止"><el-date-picker v-model="form.apply_deadline" type="datetime" value-format="YYYY-MM-DDTHH:mm" format="YYYY-MM-DD HH:mm" placeholder="不设置则长期开放" style="width: 100%" /></el-form-item>
        <el-form-item label="报名状态">
          <el-select v-model="form.enroll_status" style="width: 100%">
            <el-option v-for="item in enrollStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
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
.course-manager-card :deep(.el-card__body) { padding-top: 18px; }
.course-manager-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; flex-wrap: wrap; }
.course-manager-header__main { display: grid; gap: 6px; }
.course-manager-header__eyebrow { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 800; color: #6c86ab; }
.course-manager-header__title { font-size: 22px; line-height: 1.2; font-weight: 800; color: #22395b; }
.course-manager-header__desc { max-width: 520px; font-size: 13px; line-height: 1.7; color: #667d9b; }
.course-manager-header__actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.course-manager-search { width: 240px; }
.course-manager-filter { width: 140px; }
.course-manager-stats { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 14px; font-size: 13px; color: var(--app-text-soft); }
.course-table-wrap { width: 100%; max-width: 100%; min-width: 0; overflow-x: auto; }
.course-cell { display: grid; gap: 6px; }
.course-cell strong { color: var(--app-text-main); font-size: 15px; }
.course-cell span, .course-setting__item { color: #667d9b; line-height: 1.6; }
.course-setting { display: grid; gap: 6px; }
.course-row-actions { display: flex; gap: 6px; }
.course-manager-pager { display: flex; justify-content: flex-end; margin-top: 12px; }
@media (max-width: 768px) {
  .course-manager-header__actions { width: 100%; }
  .course-manager-search, .course-manager-filter { width: 100%; }
}
</style>
