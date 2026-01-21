<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type KP = { id: number; subject: string; grade: string; code: string; title: string; description: string };

const props = defineProps<{ subject: string; grade: string }>();

const loading = ref(false);
const kps = ref<KP[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);

const dialogOpen = ref(false);
const editing = ref<KP | null>(null);
const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
});

const isEdit = computed(() => Boolean(editing.value));

async function load() {
  loading.value = true;
  try {
    const res = await api.get(
      `/admin/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&page=${page.value}&page_size=${pageSize}`
    );
    kps.value = res.data.items ?? [];
    total.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
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
  dialogOpen.value = true;
}

function openEdit(row: KP) {
  editing.value = row;
  form.id = row.id;
  form.code = row.code;
  form.title = row.title;
  form.description = row.description;
  dialogOpen.value = true;
}

async function save() {
  try {
    if (isEdit.value) {
      await api.put(`/admin/kps/${form.id}`, {
        code: form.code,
        title: form.title,
        description: form.description,
      });
      ElMessage.success("已更新");
    } else {
      await api.post("/admin/kps", {
        subject: props.subject,
        grade: props.grade,
        code: form.code,
        title: form.title,
        description: form.description,
      });
      ElMessage.success("已新增");
    }
    dialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  }
}

async function remove(row: KP) {
  try {
    await api.delete(`/admin/kps/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败（可能存在先修边/题目/资源引用）");
  }
}

watch(
  () => [props.subject, props.grade],
  () => {
    page.value = 1;
    load();
  },
  { immediate: true }
);

onMounted(() => load());
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>知识点管理</div>
        <div style="display: flex; gap: 8px">
          <el-button @click="load" :loading="loading">刷新</el-button>
          <el-button type="primary" @click="openAdd">新增</el-button>
        </div>
      </div>
    </template>

    <el-table :data="kps" size="small" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="code" label="编码" width="160" />
      <el-table-column prop="title" label="标题" width="180" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
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

    <el-dialog v-model="dialogOpen" :title="isEdit ? '编辑知识点' : '新增知识点'" width="560px">
      <el-form label-width="80px">
        <el-form-item label="编码">
          <el-input v-model="form.code" placeholder="例如 MATH-G2-DER-013" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
