<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type KP = {
  id: number;
  subject: string;
  grade: string;
  code: string;
  title: string;
  description: string;
  chapter?: string;
  ability_tag?: string;
  literacy_tag?: string;
  importance?: number;
  difficulty?: number;
};

const props = defineProps<{ subject: string; grade: string }>();

const loading = ref(false);
const kps = ref<KP[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);
const keyword = ref("");

const dialogOpen = ref(false);
const editing = ref<KP | null>(null);
const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
  chapter: "",
  ability_tag: "",
  literacy_tag: "",
  importance: 0.5,
  difficulty: 0.5,
});

const isEdit = computed(() => Boolean(editing.value));

async function load() {
  loading.value = true;
  try {
    const query = new URLSearchParams({
      subject: props.subject,
      grade: props.grade,
      page: String(page.value),
      page_size: String(pageSize),
    });
    if (keyword.value.trim()) query.set("keyword", keyword.value.trim());
    const res = await api.get(`/admin/kps?${query.toString()}`);
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
  Object.assign(form, {
    id: 0,
    code: "",
    title: "",
    description: "",
    chapter: "",
    ability_tag: "",
    literacy_tag: "",
    importance: 0.5,
    difficulty: 0.5,
  });
  dialogOpen.value = true;
}

function openEdit(row: KP) {
  editing.value = row;
  Object.assign(form, {
    id: row.id,
    code: row.code,
    title: row.title,
    description: row.description,
    chapter: row.chapter ?? "",
    ability_tag: row.ability_tag ?? "",
    literacy_tag: row.literacy_tag ?? "",
    importance: row.importance ?? 0.5,
    difficulty: row.difficulty ?? 0.5,
  });
  dialogOpen.value = true;
}

async function save() {
  try {
    if (isEdit.value) {
      await api.put(`/admin/kps/${form.id}`, {
        code: form.code,
        title: form.title,
        description: form.description,
        chapter: form.chapter,
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
      });
      ElMessage.success("已更新");
    } else {
      await api.post("/admin/kps", {
        subject: props.subject,
        grade: props.grade,
        code: form.code,
        title: form.title,
        description: form.description,
        chapter: form.chapter,
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
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
  <el-card class="panel-card" shadow="never">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap">
        <div>知识点管理</div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <el-input
            v-model="keyword"
            placeholder="搜索编码/标题/描述"
            size="small"
            style="width: 220px"
            @keyup.enter="() => { page = 1; load(); }"
          />
          <el-button size="small" type="primary" @click="() => { page = 1; load(); }">搜索</el-button>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
          <el-button type="primary" @click="openAdd">新增</el-button>
        </div>
      </div>
    </template>

    <el-table :data="kps" size="small" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="code" label="编码" width="160" />
      <el-table-column prop="title" label="标题" width="180" />
      <el-table-column prop="chapter" label="章节" width="140" />
      <el-table-column prop="ability_tag" label="能力标签" width="140" />
      <el-table-column prop="literacy_tag" label="素养标签" width="140" />
      <el-table-column prop="importance" label="重要度" width="100">
        <template #default="{ row }">{{ Math.round((row.importance ?? 0.5) * 100) }}</template>
      </el-table-column>
      <el-table-column prop="difficulty" label="难度" width="100">
        <template #default="{ row }">{{ Math.round((row.difficulty ?? 0.5) * 100) }}</template>
      </el-table-column>
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

    <el-dialog v-model="dialogOpen" :title="isEdit ? '编辑知识点' : '新增知识点'" width="620px">
      <el-form label-width="80px">
        <el-form-item label="编码">
          <el-input v-model="form.code" placeholder="例如 DS-GEN-001" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="章节">
          <el-input v-model="form.chapter" placeholder="例如 第一章 / 控件" />
        </el-form-item>
        <el-form-item label="能力标签">
          <el-input v-model="form.ability_tag" placeholder="例如 逻辑分析" />
        </el-form-item>
        <el-form-item label="素养标签">
          <el-input v-model="form.literacy_tag" placeholder="例如 工程规范" />
        </el-form-item>
        <el-form-item label="重要度">
          <el-input-number v-model="form.importance" :min="0" :max="1" :step="0.05" />
        </el-form-item>
        <el-form-item label="难度">
          <el-input-number v-model="form.difficulty" :min="0" :max="1" :step="0.05" />
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
