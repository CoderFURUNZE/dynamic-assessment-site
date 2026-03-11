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
const page = ref(1);
const pageSize = 15;
const total = ref(0);
const keyword = ref("");

const dialogOpen = ref(false);
const editing = ref<Course | null>(null);
const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
  active: true,
  teacher_id: null as number | null,
});

const isEdit = computed(() => Boolean(editing.value));
const isAdmin = computed(() => getRole() === "admin");
const teacherNameMap = computed(() => {
  const map = new Map<number, string>();
  for (const item of teachers.value) {
    map.set(item.id, item.full_name || item.username);
  }
  return map;
});

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
  dialogOpen.value = true;
}

async function save() {
  try {
    if (isEdit.value) {
      await api.put(`/admin/courses/${form.id}`, {
        code: form.code,
        title: form.title,
        description: form.description,
        active: form.active,
        teacher_id: form.teacher_id,
      });
      ElMessage.success("已更新");
    } else {
      await api.post("/admin/courses", {
        code: form.code,
        title: form.title,
        description: form.description,
        active: form.active,
        teacher_id: form.teacher_id,
      });
      ElMessage.success("已新增");
    }
    dialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
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

async function toggleActive(row: Course, value: boolean) {
  try {
    await api.put(`/admin/courses/${row.id}`, { active: value });
    row.active = value;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新状态失败");
    row.active = !value;
  }
}

Promise.all([loadTeachers(), load()]);
</script>

<template>
  <el-card class="panel-card" shadow="never">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap">
        <div>课程管理</div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <el-input
            v-model="keyword"
            placeholder="搜索课程名称/编码"
            size="small"
            style="width: 220px"
            @keyup.enter="() => { page = 1; load(); }"
          />
          <el-button size="small" type="primary" @click="() => { page = 1; load(); }">搜索</el-button>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
          <el-button type="primary" @click="openAdd">新增课程</el-button>
        </div>
      </div>
    </template>

    <el-table :data="courses" size="small" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="code" label="课程编码" width="140" />
      <el-table-column prop="title" label="课程名称" width="220" />
      <el-table-column prop="description" label="课程简介" />
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
      <el-table-column prop="active" label="状态" width="140">
        <template #default="{ row }">
          <el-switch v-model="row.active" @change="(v: boolean) => toggleActive(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

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
        <el-form-item label="启用">
          <el-switch v-model="form.active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
