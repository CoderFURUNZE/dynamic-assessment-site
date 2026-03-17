<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";

type Course = {
  id: number;
  code: string;
  title: string;
  description: string;
  active: boolean;
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

type EnrolledStudent = {
  id: number;
  username: string;
  full_name: string;
  student_no?: string;
  class_name?: string;
  active: boolean;
  enrolled_at?: string;
};

type CourseApplicationRow = {
  id: number;
  course_id: number;
  course_title: string;
  student_id: number;
  student_name: string;
  status: string;
  apply_reason: string;
  review_remark: string;
  reject_reason: string;
  created_at: string;
};

const loading = ref(false);
const courses = ref<Course[]>([]);
const teachers = ref<Teacher[]>([]);
const togglingIds = ref<number[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);
const keyword = ref("");

const dialogOpen = ref(false);
const editing = ref<Course | null>(null);
const saving = ref(false);
const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
  active: true,
  teacher_id: null as number | null,
  max_students: 200,
  apply_deadline: "",
  enroll_status: "open",
});

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
const isAdmin = computed(() => getRole() === "admin");
const isTeacher = computed(() => getRole() === "teacher");
const teacherNameMap = computed(() => {
  const map = new Map<number, string>();
  for (const item of teachers.value) {
    map.set(item.id, item.full_name || item.username);
  }
  return map;
});

const studentDialogOpen = ref(false);
const studentDialogLoading = ref(false);
const studentDialogCourse = ref<Course | null>(null);
const studentRows = ref<EnrolledStudent[]>([]);

const reviewDialogOpen = ref(false);
const reviewDialogLoading = ref(false);
const reviewRows = ref<CourseApplicationRow[]>([]);
const rejectDialogOpen = ref(false);
const rejecting = ref<CourseApplicationRow | null>(null);
const rejectReason = ref("");

async function loadTeachers() {
  if (!isAdmin.value) {
    teachers.value = [];
    return;
  }
  const res = await api.get("/admin/users?page=1&page_size=200");
  teachers.value = (res.data.items ?? []).filter((item: Teacher) => item.role === "teacher");
}

async function load() {
  loading.value = true;
  try {
    const query = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize),
    });
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
  form.teacher_id = row.teacher_id ?? null;
  form.max_students = Number(row.max_students ?? 200);
  form.apply_deadline = row.apply_deadline ? row.apply_deadline.slice(0, 16) : "";
  form.enroll_status = row.enroll_status || "open";
  dialogOpen.value = true;
}

async function save() {
  if (saving.value) return;
  const normalizedCode = form.code.trim();
  const normalizedTitle = form.title.trim();
  const payload = {
    code: normalizedCode,
    title: normalizedTitle,
    description: form.description,
    active: form.active,
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
      ElMessage.success("已更新");
    } else {
      await api.post("/admin/courses", payload);
      ElMessage.success("已新增");
    }
    dialogOpen.value = false;
  } catch (e: any) {
    const status = Number(e?.response?.status ?? 0);
    const detail = e?.response?.data?.detail ?? "保存失败";
    // 处理“后端已保存但响应异常/超时”的假失败：只在 5xx 或无状态码时回查
    if (!status || status >= 500) {
      try {
        const probe = await api.get("/admin/courses", {
          params: {
            page: 1,
            page_size: 100,
            keyword: payload.code || payload.title,
          },
        });
        const rows: Course[] = probe.data?.items ?? [];
        const matched = isEdit.value
          ? rows.find((row) => row.id === form.id)
          : rows.find((row) => row.code === payload.code && row.title === payload.title);
        if (
          matched
          && matched.code === payload.code
          && matched.title === payload.title
          && (matched.description ?? "") === (payload.description ?? "")
          && Boolean(matched.active) === Boolean(payload.active)
          && Number(matched.max_students ?? 0) === Number(payload.max_students)
          && String(matched.enroll_status || "open").toLowerCase() === String(payload.enroll_status || "open").toLowerCase()
          && normalizeIsoMinute(matched.apply_deadline) === normalizeIsoMinute(payload.apply_deadline)
        ) {
          ElMessage.success(isEdit.value ? "已更新（已自动确认）" : "已新增（已自动确认）");
          dialogOpen.value = false;
          await load();
          return;
        }
      } catch {
        // ignore verify failure and fall through to normal error
      }
    }
    ElMessage.error(detail);
    return;
  } finally {
    saving.value = false;
  }
  try {
    await load();
  } catch {
    ElMessage.warning("课程已保存，但列表刷新失败，请手动点“刷新”");
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

async function openStudentDialog(row: Course) {
  studentDialogCourse.value = row;
  studentDialogOpen.value = true;
  studentDialogLoading.value = true;
  try {
    const res = await api.get(`/graph/courses/${row.id}/students`);
    studentRows.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程学生失败");
    studentRows.value = [];
  } finally {
    studentDialogLoading.value = false;
  }
}

async function removeStudent(row: EnrolledStudent) {
  if (!studentDialogCourse.value) return;
  try {
    await api.delete(`/graph/courses/${studentDialogCourse.value.id}/students/${row.id}`);
    ElMessage.success("学生已移出课程");
    studentRows.value = studentRows.value.filter((item) => item.id !== row.id);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "移出学生失败");
  }
}

async function openReviewDialog() {
  reviewDialogOpen.value = true;
  reviewDialogLoading.value = true;
  try {
    const res = await api.get("/enrollment/teacher/applications", {
      params: {
        status: "pending",
        page: 1,
        page_size: 100,
      },
    });
    reviewRows.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载待审核报名失败");
    reviewRows.value = [];
  } finally {
    reviewDialogLoading.value = false;
  }
}

async function approveApplication(row: CourseApplicationRow) {
  try {
    await api.post(`/enrollment/teacher/applications/${row.id}/approve`, { review_remark: "审核通过" });
    ElMessage.success("已审核通过");
    reviewRows.value = reviewRows.value.filter((item) => item.id !== row.id);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "审核通过失败");
  }
}

function openRejectDialog(row: CourseApplicationRow) {
  rejecting.value = row;
  rejectReason.value = "";
  rejectDialogOpen.value = true;
}

async function submitReject() {
  if (!rejecting.value) return;
  if (!rejectReason.value.trim()) {
    ElMessage.warning("请填写拒绝原因");
    return;
  }
  try {
    await api.post(`/enrollment/teacher/applications/${rejecting.value.id}/reject`, {
      reject_reason: rejectReason.value.trim(),
      review_remark: "审核拒绝",
    });
    ElMessage.success("已拒绝该报名");
    reviewRows.value = reviewRows.value.filter((item) => item.id !== rejecting.value?.id);
    rejectDialogOpen.value = false;
    rejecting.value = null;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "审核拒绝失败");
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
  return (
    enrollStatusOptions.find((item) => item.value === normalized)?.label
    ?? normalized
  );
}

async function probeCourseActive(row: Course) {
  const probe = await api.get("/admin/courses", {
    params: {
      page: 1,
      page_size: 100,
      keyword: row.code || row.title || "",
    },
  });
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
      } catch {
        // ignore probe error and fallthrough
      }
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
  <el-card class="panel-card" shadow="never">
    <template #header>
      <div class="course-manager-header">
        <div class="course-manager-header__main">
          <div class="course-manager-header__eyebrow">Course Admin</div>
          <div class="course-manager-header__title">课程管理</div>
          <div class="course-manager-header__desc">统一维护课程、报名设置、负责教师和课程启用状态。</div>
        </div>
        <div class="course-manager-header__actions">
          <el-input
            v-model="keyword"
            placeholder="搜索课程名称/编码"
            size="small"
            class="course-manager-search"
            @keyup.enter="() => { page = 1; load(); }"
          />
          <el-button size="small" type="primary" @click="() => { page = 1; load(); }">搜索</el-button>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
          <el-button v-if="isTeacher" size="small" type="warning" @click="openReviewDialog">报名审核</el-button>
          <el-button type="primary" @click="openAdd">新增课程</el-button>
        </div>
      </div>
    </template>

    <div class="course-table-wrap">
      <el-table :data="courses" size="small" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="code" label="课程编码" width="140" />
        <el-table-column prop="title" label="课程名称" width="220" />
        <el-table-column prop="description" label="课程简介" min-width="240" />
        <el-table-column label="报名设置" min-width="220">
          <template #default="{ row }">
            <div class="course-setting">
              <span class="course-setting__item">名额：{{ row.max_students ?? 200 }}</span>
              <span class="course-setting__item">状态：{{ enrollStatusLabel(row.enroll_status) }}</span>
              <span class="course-setting__item">截止：{{ row.apply_deadline ? row.apply_deadline.replace("T", " ").slice(0, 16) : "未设置" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="负责人" width="160">
          <template #default="{ row }">
            {{
              row.teacher_id
                ? teacherNameMap.get(row.teacher_id) || (isAdmin ? `教师#${row.teacher_id}` : "当前教师")
                : isAdmin
                  ? "未分配"
                  : "当前教师"
            }}
          </template>
        </el-table-column>
        <el-table-column v-if="isTeacher" label="学生管理" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openStudentDialog(row)">查看学生</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="active" label="状态" width="120">
          <template #default="{ row }">
            <el-switch
              :model-value="row.active"
              :loading="isToggling(row.id)"
              @change="(v: boolean) => toggleActive(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div style="display: flex; justify-content: flex-end; margin-top: 10px">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="total"
        v-model:current-page="page"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="dialogOpen" :title="isEdit ? '编辑课程' : '新增课程'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="课程编码">
          <el-input v-model="form.code" placeholder="如 DS / OS / CN" />
        </el-form-item>
        <el-form-item label="课程名称">
          <el-input v-model="form.title" placeholder="如 数据结构" />
        </el-form-item>
        <el-form-item v-if="isAdmin" label="负责人">
          <el-select v-model="form.teacher_id" clearable placeholder="选择教师" style="width: 100%">
            <el-option
              v-for="teacher in teachers"
              :key="teacher.id"
              :label="teacher.full_name || teacher.username"
              :value="teacher.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="课程简介">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="课程名额">
          <el-input-number v-model="form.max_students" :min="1" :max="9999" style="width: 100%" />
        </el-form-item>
        <el-form-item label="报名截止">
          <el-date-picker
            v-model="form.apply_deadline"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm"
            format="YYYY-MM-DD HH:mm"
            placeholder="不设置则长期开放"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="报名状态">
          <el-select v-model="form.enroll_status" style="width: 100%">
            <el-option
              v-for="item in enrollStatusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="studentDialogOpen"
      :title="studentDialogCourse ? `${studentDialogCourse.title} · 已报名学生` : '课程学生'"
      width="760px"
    >
      <el-table :data="studentRows" size="small" v-loading="studentDialogLoading" style="width: 100%">
        <el-table-column prop="username" label="账号" min-width="120" />
        <el-table-column label="姓名" min-width="140">
          <template #default="{ row }">{{ row.full_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="学号" min-width="140">
          <template #default="{ row }">{{ row.student_no || "-" }}</template>
        </el-table-column>
        <el-table-column label="班级" min-width="140">
          <template #default="{ row }">{{ row.class_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">{{ row.active ? "启用" : "停用" }}</template>
        </el-table-column>
        <el-table-column label="报名时间" min-width="180">
          <template #default="{ row }">{{ row.enrolled_at ? row.enrolled_at.replace("T", " ").slice(0, 16) : "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeStudent(row)">移出</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!studentDialogLoading && studentRows.length === 0" class="course-student-empty">当前课程还没有学生报名。</div>
    </el-dialog>

    <el-dialog v-model="reviewDialogOpen" title="待审核报名" width="860px">
      <el-table :data="reviewRows" size="small" v-loading="reviewDialogLoading" style="width: 100%">
        <el-table-column prop="course_title" label="课程" min-width="160" />
        <el-table-column prop="student_name" label="学生" min-width="120" />
        <el-table-column prop="apply_reason" label="报名理由" min-width="220" />
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at?.replace("T", " ").slice(0, 16) || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="approveApplication(row)">通过</el-button>
            <el-button size="small" type="danger" @click="openRejectDialog(row)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!reviewDialogLoading && reviewRows.length === 0" class="course-student-empty">当前没有待审核报名。</div>
    </el-dialog>

    <el-dialog v-model="rejectDialogOpen" title="填写拒绝原因" width="520px">
      <el-input
        v-model="rejectReason"
        type="textarea"
        :rows="4"
        placeholder="请填写拒绝原因（必填）"
      />
      <template #footer>
        <el-button @click="rejectDialogOpen = false">取消</el-button>
        <el-button type="danger" @click="submitReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.course-manager-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
}

.course-manager-header__main {
  display: grid;
  gap: 6px;
}

.course-manager-header__eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #6c86ab;
}

.course-manager-header__title {
  font-size: 22px;
  line-height: 1.2;
  font-weight: 800;
  color: #22395b;
}

.course-manager-header__desc {
  max-width: 520px;
  font-size: 13px;
  line-height: 1.7;
  color: #667d9b;
}

.course-manager-header__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.course-manager-search {
  width: 220px;
}

.course-table-wrap {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.course-setting {
  display: grid;
  gap: 6px;
}

.course-setting__item {
  color: #667d9b;
  line-height: 1.5;
}

.course-student-empty {
  padding: 16px 0 4px;
  color: #7d8ea4;
}

@media (max-width: 768px) {
  .course-manager-header__actions {
    width: 100%;
  }

  .course-manager-search {
    width: 100%;
  }
}
</style>
