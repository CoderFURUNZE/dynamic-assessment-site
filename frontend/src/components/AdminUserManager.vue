<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HintButton from "./HintButton.vue";

const props = withDefaults(defineProps<{ mode?: "users" | "teachers" }>(), {
  mode: "users",
});

type UserRow = {
  id: number;
  username: string;
  role: string;
  active: boolean;
  full_name: string;
  student_no: string;
  class_name: string;
  phone?: string | null;
  wechat_openid?: string | null;
};

type ImportPreview = {
  role: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  required_fields: string[];
  detected_fields: string[];
  matched_courses: Array<{
    course_id: number;
    course_title: string;
    course_code: string;
    target_class: string;
  }>;
  warnings: string[];
  errors: string[];
};

type ImportResult = {
  role: string;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  created_rows: number;
  updated_rows: number;
  auto_enrolled_rows: number;
  errors: string[];
};

const loading = ref(false);
const users = ref<UserRow[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);
const dialogOpen = ref(false);
const createDialogOpen = ref(false);
const importLoading = ref(false);
const previewDialogOpen = ref(false);
const importResultDialogOpen = ref(false);
const keyword = ref("");
const statusFilter = ref<"all" | "active" | "inactive">("all");
const importInputRef = ref<HTMLInputElement | null>(null);
const pendingImportFile = ref<File | null>(null);
const importPreview = ref<ImportPreview | null>(null);
const importResult = ref<ImportResult | null>(null);

const form = reactive({
  id: 0,
  username: "",
  role: "student",
  active: true,
  full_name: "",
  student_no: "",
  class_name: "",
  phone: "",
  password: "",
});

const createForm = reactive({
  username: "",
  role: props.mode === "teachers" ? "teacher" : "student",
  active: true,
  full_name: "",
  student_no: "",
  class_name: "",
  phone: "",
  password: "",
});

const titleText = computed(() => (props.mode === "teachers" ? "教师管理" : "用户管理"));
const roleFilter = computed(() => (props.mode === "teachers" ? "teacher" : ""));
const createLabel = computed(() => (props.mode === "teachers" ? "新增教师" : "新增用户"));
const importRole = computed(() => (props.mode === "teachers" ? "teacher" : "student"));
const importLabel = computed(() => (props.mode === "teachers" ? "导入教师" : "导入学生"));
const filteredUsers = computed(() => {
  const q = keyword.value.trim().toLowerCase();
  return users.value.filter((row) => {
    const matchesKeyword = !q || [row.username, row.full_name, row.student_no, row.class_name, row.phone || ""].join(" ").toLowerCase().includes(q);
    const matchesStatus = statusFilter.value === "all" || (statusFilter.value === "active" ? row.active : !row.active);
    return matchesKeyword && matchesStatus;
  });
});

async function load() {
  loading.value = true;
  try {
    const qs = new URLSearchParams({ page: String(page.value), page_size: String(pageSize) });
    if (roleFilter.value) qs.set("role", roleFilter.value);
    const res = await api.get(`/admin/users?${qs.toString()}`);
    users.value = res.data.items ?? [];
    total.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载用户失败");
  } finally {
    loading.value = false;
  }
}

function openEdit(row: UserRow) {
  form.id = row.id;
  form.username = row.username;
  form.role = row.role;
  form.active = row.active;
  form.full_name = row.full_name;
  form.student_no = row.student_no;
  form.class_name = row.class_name;
  form.phone = row.phone ?? "";
  form.password = "";
  dialogOpen.value = true;
}

function openCreate() {
  createForm.username = "";
  createForm.role = props.mode === "teachers" ? "teacher" : "student";
  createForm.active = true;
  createForm.full_name = "";
  createForm.student_no = "";
  createForm.class_name = "";
  createForm.phone = "";
  createForm.password = "";
  createDialogOpen.value = true;
}

async function save() {
  try {
    await api.put(`/admin/users/${form.id}`, {
      role: props.mode === "teachers" ? "teacher" : form.role,
      active: form.active,
      full_name: form.full_name,
      student_no: form.student_no,
      class_name: form.class_name,
      phone: form.phone || undefined,
      password: form.password || undefined,
    });
    ElMessage.success("已保存");
    dialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  }
}

async function createUser() {
  try {
    await api.post("/admin/users", {
      username: createForm.username,
      role: props.mode === "teachers" ? "teacher" : createForm.role,
      active: createForm.active,
      full_name: createForm.full_name,
      student_no: createForm.student_no,
      class_name: createForm.class_name,
      phone: createForm.phone || undefined,
      password: createForm.password,
    });
    ElMessage.success("账号已创建");
    createDialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "创建失败");
  }
}

async function toggleActive(row: UserRow, active: boolean) {
  try {
    await api.put(`/admin/users/${row.id}`, { active });
    ElMessage.success(active ? "已启用" : "已禁用");
    row.active = active;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新状态失败");
    row.active = !active;
  }
}

async function remove(row: UserRow) {
  try {
    await api.delete(`/admin/users/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败");
  }
}

async function downloadTemplate() {
  try {
    const res = await api.get(`/admin/users/import-template?role=${importRole.value}`, {
      responseType: "blob",
    });
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${importRole.value}_import_template.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "下载导入模板失败");
  }
}

function triggerImport() {
  importInputRef.value?.click();
}

async function handleImportChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  importLoading.value = true;
  try {
    const form = new FormData();
    form.append("role", importRole.value);
    form.append("file", file);
    const { data } = await api.post("/admin/users/import/preview", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    pendingImportFile.value = file;
    importPreview.value = data;
    previewDialogOpen.value = true;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导入预校验失败");
  } finally {
    importLoading.value = false;
    target.value = "";
  }
}

async function confirmImport() {
  if (!pendingImportFile.value) return;
  importLoading.value = true;
  try {
    const form = new FormData();
    form.append("role", importRole.value);
    form.append("file", pendingImportFile.value);
    const { data } = await api.post("/admin/users/import", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    importResult.value = data;
    importResultDialogOpen.value = true;
    previewDialogOpen.value = false;
    pendingImportFile.value = null;
    ElMessage.success(`导入完成：成功 ${data.success_rows} 条，失败 ${data.failed_rows} 条，新增 ${data.created_rows} 条，更新 ${data.updated_rows} 条`);
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "批量导入失败");
  } finally {
    importLoading.value = false;
  }
}

onMounted(() => load());
watch(() => props.mode, () => { page.value = 1; load(); });
</script>

<template>
  <el-card class="panel-card admin-user-card" shadow="never">
    <template #header>
      <div class="admin-user-card__header">
        <div class="admin-user-card__title-block">
          <div class="admin-user-card__eyebrow">{{ props.mode === 'teachers' ? 'Teacher Admin' : 'User Admin' }}</div>
          <div class="admin-user-card__title">{{ titleText }}</div>
          <div class="admin-user-card__desc">列表、筛选和新增操作都放在一处，减少来回找按钮。</div>
        </div>
        <div class="admin-user-card__toolbar">
          <el-input v-model="keyword" placeholder="搜索用户名 / 姓名 / 学号 / 班级" clearable class="admin-user-card__search" />
          <el-select v-model="statusFilter" class="admin-user-card__status">
            <el-option label="全部状态" value="all" />
            <el-option label="仅启用" value="active" />
            <el-option label="仅禁用" value="inactive" />
          </el-select>
          <HintButton tip="重新加载用户列表" @click="load" :loading="loading">刷新</HintButton>
          <HintButton tip="下载批量导入模板" @click="downloadTemplate">下载模板</HintButton>
          <HintButton tip="上传 CSV 或 XLSX 批量导入" @click="triggerImport" :loading="importLoading">{{ importLabel }}</HintButton>
          <HintButton type="primary" tip="新建一条账号记录" @click="openCreate">{{ createLabel }}</HintButton>
          <input ref="importInputRef" type="file" accept=".csv,.xlsx" class="admin-user-card__file-input" @change="handleImportChange" />
        </div>
      </div>
    </template>

    <div class="admin-user-card__summary">
      <span>当前页 {{ users.length }} 条</span>
      <span>筛选后 {{ filteredUsers.length }} 条</span>
      <span>总计 {{ total }} 条</span>
    </div>

    <el-table :data="filteredUsers" size="small" v-loading="loading" class="admin-user-card__table">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="role" label="角色" width="100" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-switch
            v-model="row.active"
            active-text="启用"
            inactive-text="禁用"
            @change="(val: any) => toggleActive(row, Boolean(val))"
            :disabled="row.username === 'admin'"
          />
        </template>
      </el-table-column>
      <el-table-column prop="full_name" label="姓名" />
      <el-table-column prop="student_no" label="学号" />
      <el-table-column prop="class_name" label="班级" />
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column prop="wechat_openid" label="微信OpenID" width="180" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <div class="admin-user-card__row-actions">
            <HintButton size="small" tip="编辑这条账号信息" @click="openEdit(row)">编辑</HintButton>
            <HintButton size="small" type="danger" tip="删除这条账号记录" @click="remove(row)" :disabled="row.username === 'admin'">删除</HintButton>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="admin-user-card__pager">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="total"
        v-model:current-page="page"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="dialogOpen" title="编辑用户" width="520px">
      <el-form label-width="90px">
        <el-form-item label="用户名"><el-input v-model="form.username" disabled /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%" :disabled="props.mode === 'teachers'">
            <el-option label="admin" value="admin" />
            <el-option label="teacher" value="teacher" />
            <el-option label="student" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态"><el-switch v-model="form.active" active-text="启用" inactive-text="禁用" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.full_name" /></el-form-item>
        <el-form-item label="学号"><el-input v-model="form.student_no" /></el-form-item>
        <el-form-item label="班级"><el-input v-model="form.class_name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" placeholder="留空表示未绑定" /></el-form-item>
        <el-form-item label="重置密码"><el-input v-model="form.password" placeholder="留空则不修改" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <HintButton @click="dialogOpen = false">取消</HintButton>
        <HintButton type="primary" @click="save">保存</HintButton>
      </template>
    </el-dialog>

    <el-dialog v-model="createDialogOpen" :title="createLabel" width="520px">
      <el-form label-width="90px">
        <el-form-item label="用户名"><el-input v-model="createForm.username" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" style="width: 100%" :disabled="props.mode === 'teachers'">
            <el-option label="teacher" value="teacher" />
            <el-option label="student" value="student" />
            <el-option label="admin" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态"><el-switch v-model="createForm.active" active-text="启用" inactive-text="禁用" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="createForm.full_name" /></el-form-item>
        <el-form-item label="学号"><el-input v-model="createForm.student_no" /></el-form-item>
        <el-form-item label="班级"><el-input v-model="createForm.class_name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="createForm.phone" placeholder="留空表示未绑定" /></el-form-item>
        <el-form-item label="初始密码"><el-input v-model="createForm.password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <HintButton @click="createDialogOpen = false">取消</HintButton>
        <HintButton type="primary" @click="createUser">创建</HintButton>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialogOpen" :title="`${importLabel}预校验`" width="720px">
      <template v-if="importPreview">
        <div class="admin-user-card__summary">
          <span>总行数 {{ importPreview.total_rows }}</span>
          <span>可导入 {{ importPreview.valid_rows }}</span>
          <span>异常 {{ importPreview.invalid_rows }}</span>
        </div>
        <div class="admin-user-card__preview-grid">
          <div class="admin-user-card__preview-box">
            <strong>必填字段</strong>
            <div>{{ importPreview.required_fields.join(" / ") || "无" }}</div>
          </div>
          <div class="admin-user-card__preview-box">
            <strong>识别字段</strong>
            <div>{{ importPreview.detected_fields.join(" / ") || "无" }}</div>
          </div>
        </div>
        <div v-if="importPreview.matched_courses.length" class="admin-user-card__preview-list">
          <strong>将自动分配到以下课程</strong>
          <div v-for="item in importPreview.matched_courses" :key="`${item.course_id}-${item.target_class}`">
            {{ item.course_code }} / {{ item.course_title }} / 班级：{{ item.target_class }}
          </div>
        </div>
        <div v-if="importPreview.warnings.length" class="admin-user-card__preview-list">
          <strong>预警信息</strong>
          <div v-for="item in importPreview.warnings" :key="item">{{ item }}</div>
        </div>
        <div v-if="importPreview.errors.length" class="admin-user-card__preview-list admin-user-card__preview-list--error">
          <strong>错误明细</strong>
          <div v-for="item in importPreview.errors" :key="item">{{ item }}</div>
        </div>
      </template>
      <template #footer>
        <HintButton @click="previewDialogOpen = false">取消</HintButton>
        <HintButton type="primary" :disabled="Boolean(importPreview && importPreview.valid_rows === 0)" :loading="importLoading" @click="confirmImport">
          确认导入
        </HintButton>
      </template>
    </el-dialog>

    <el-dialog v-model="importResultDialogOpen" :title="`${importLabel}结果`" width="720px">
      <template v-if="importResult">
        <div class="admin-user-card__summary">
          <span>总行数 {{ importResult.total_rows }}</span>
          <span>成功 {{ importResult.success_rows }}</span>
          <span>失败 {{ importResult.failed_rows }}</span>
          <span>新增 {{ importResult.created_rows }}</span>
          <span>更新 {{ importResult.updated_rows }}</span>
          <span v-if="importRole === 'student'">自动分配课程 {{ importResult.auto_enrolled_rows }}</span>
        </div>
        <div v-if="importResult.errors.length" class="admin-user-card__preview-list admin-user-card__preview-list--error">
          <strong>错误明细</strong>
          <div v-for="item in importResult.errors" :key="item">{{ item }}</div>
        </div>
      </template>
      <template #footer>
        <HintButton type="primary" @click="importResultDialogOpen = false">关闭</HintButton>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.admin-user-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.admin-user-card__title-block { display: grid; gap: 6px; }
.admin-user-card__eyebrow { font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: #6c86ab; }
.admin-user-card__title { font-size: 22px; font-weight: 800; color: var(--app-text-main); }
.admin-user-card__desc { color: var(--app-text-soft); font-size: 13px; }
.admin-user-card__toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.admin-user-card__search { width: 260px; }
.admin-user-card__status { width: 130px; }
.admin-user-card__file-input { display: none; }
.admin-user-card__summary { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 12px; font-size: 13px; color: var(--app-text-soft); }
.admin-user-card__preview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.admin-user-card__preview-box { padding: 12px 14px; border: 1px solid #dbe6f4; border-radius: 14px; background: #f8fbff; display: grid; gap: 6px; color: var(--app-text-soft); }
.admin-user-card__preview-box strong,
.admin-user-card__preview-list strong { color: var(--app-text-main); }
.admin-user-card__preview-list { display: grid; gap: 6px; padding: 12px 14px; border: 1px solid #dbe6f4; border-radius: 14px; background: #f8fbff; margin-bottom: 12px; color: var(--app-text-soft); max-height: 280px; overflow: auto; }
.admin-user-card__preview-list--error { border-color: #f0d0d0; background: #fff8f8; color: #b44b4b; }
.admin-user-card__row-actions { display: flex; gap: 6px; }
.admin-user-card__pager { display: flex; justify-content: flex-end; margin-top: 12px; }
@media (max-width: 768px) {
  .admin-user-card__search,
  .admin-user-card__status { width: 100%; }
  .admin-user-card__toolbar { width: 100%; }
  .admin-user-card__preview-grid { grid-template-columns: 1fr; }
}
</style>
