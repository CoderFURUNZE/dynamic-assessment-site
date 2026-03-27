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

const loading = ref(false);
const users = ref<UserRow[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);
const dialogOpen = ref(false);
const createDialogOpen = ref(false);
const editing = ref<UserRow | null>(null);

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

const titleText = computed(() => (props.mode === "teachers" ? "老师管理" : "用户管理"));
const roleFilter = computed(() => (props.mode === "teachers" ? "teacher" : ""));

async function load() {
  loading.value = true;
  try {
    const qs = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize),
    });
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
  editing.value = row;
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

onMounted(() => load());

watch(
  () => props.mode,
  () => {
    page.value = 1;
    load();
  }
);
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>{{ titleText }}</div>
        <div style="display: flex; gap: 8px">
          <HintButton type="primary" tip="新增一个老师或学生账号。" @click="openCreate">新增{{ props.mode === "teachers" ? "老师" : "用户" }}</HintButton>
          <HintButton tip="刷新用户列表。" @click="load" :loading="loading">刷新</HintButton>
        </div>
      </div>
    </template>

    <el-table :data="users" size="small" v-loading="loading" style="width: 100%">
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
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <HintButton size="small" tip="编辑该用户的姓名、班级、手机号和状态。" @click="openEdit(row)">编辑</HintButton>
          <HintButton size="small" type="danger" tip="删除该用户账号，管理员默认账号不可删。" @click="remove(row)" :disabled="row.username === 'admin'">删除</HintButton>
        </template>
      </el-table-column>
    </el-table>

    <div style="display: flex; justify-content: flex-end; margin-top: 8px">
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
        <el-form-item label="用户名">
          <el-input v-model="form.username" disabled />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%" :disabled="props.mode === 'teachers'">
            <el-option label="admin" value="admin" />
            <el-option label="teacher" value="teacher" />
            <el-option label="student" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="学号">
          <el-input v-model="form.student_no" />
        </el-form-item>
        <el-form-item label="班级">
          <el-input v-model="form.class_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="留空表示未绑定" />
        </el-form-item>
        <el-form-item label="重置密码">
          <el-input v-model="form.password" placeholder="留空则不修改" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <HintButton tip="关闭编辑窗口，不保存当前修改。" @click="dialogOpen = false">取消</HintButton>
        <HintButton type="primary" tip="保存当前用户信息修改。" @click="save">保存</HintButton>
      </template>
    </el-dialog>

    <el-dialog v-model="createDialogOpen" :title="`新增${props.mode === 'teachers' ? '老师' : '用户'}`" width="520px">
      <el-form label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" style="width: 100%" :disabled="props.mode === 'teachers'">
            <el-option label="teacher" value="teacher" />
            <el-option label="student" value="student" />
            <el-option label="admin" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="createForm.active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="createForm.full_name" />
        </el-form-item>
        <el-form-item label="学号">
          <el-input v-model="createForm.student_no" />
        </el-form-item>
        <el-form-item label="班级">
          <el-input v-model="createForm.class_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="createForm.phone" placeholder="留空表示未绑定" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="createForm.password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <HintButton tip="关闭创建窗口，不提交。" @click="createDialogOpen = false">取消</HintButton>
        <HintButton type="primary" tip="创建这个账号并写入系统。" @click="createUser">创建</HintButton>
      </template>
    </el-dialog>
  </el-card>
</template>
