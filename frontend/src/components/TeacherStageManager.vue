<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type Stage = {
  id: number;
  course_id: number;
  subject: string;
  grade: string;
  title: string;
  stage_order: number;
  starts_at?: string | null;
  ends_at?: string | null;
  description: string;
  created_at: string;
};

const props = defineProps<{
  courseId: number | null;
  subject: string;
  grade: string;
}>();

const emit = defineEmits<{
  (e: "stage-changed"): void;
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

function resetForm() {
  form.title = "";
  form.stage_order = (stages.value.at(-1)?.stage_order ?? 0) + 1;
  form.starts_at = "";
  form.ends_at = "";
  form.description = "";
}

async function load() {
  if (!props.courseId) {
    stages.value = [];
    return;
  }
  loading.value = true;
  try {
    const res = await api.get(`/stages/courses/${props.courseId}`);
    stages.value = res.data ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载阶段列表失败");
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  editingId.value = null;
  resetForm();
  dialogOpen.value = true;
}

function openEdit(row: Stage) {
  editingId.value = row.id;
  form.title = row.title;
  form.stage_order = row.stage_order;
  form.starts_at = row.starts_at ? row.starts_at.slice(0, 10) : "";
  form.ends_at = row.ends_at ? row.ends_at.slice(0, 10) : "";
  form.description = row.description ?? "";
  dialogOpen.value = true;
}

async function save() {
  if (!props.courseId) {
    ElMessage.warning("请先选择课程");
    return;
  }

  const payload = {
    grade: props.grade,
    title: form.title,
    stage_order: form.stage_order,
    starts_at: form.starts_at || null,
    ends_at: form.ends_at || null,
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
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存阶段失败");
    return;
  }

  try {
    await load();
  } catch {
    ElMessage.warning("阶段列表刷新失败");
  }
  window.dispatchEvent(new CustomEvent("da:teacher-stage-changed", { detail: { courseId: props.courseId } }));
  emit("stage-changed");
}

async function remove(row: Stage) {
  try {
    await api.delete(`/stages/${row.id}`);
    ElMessage.success("阶段已删除");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除阶段失败");
    return;
  }

  try {
    await load();
  } catch {
    ElMessage.warning("阶段列表刷新失败");
  }
  window.dispatchEvent(new CustomEvent("da:teacher-stage-changed", { detail: { courseId: props.courseId } }));
  emit("stage-changed");
}

watch(
  () => props.courseId,
  () => {
    dialogOpen.value = false;
    resetForm();
    load();
  },
  { immediate: true }
);
</script>

<template>
  <el-card class="panel-card" shadow="never">
    <template #header>
      <div class="stage-header">
        <div>
          <div class="stage-title">阶段管理</div>
        </div>
        <div class="stage-actions">
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
          <el-button type="primary" size="small" @click="openAdd" :disabled="!courseId">新增阶段</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!courseId" description="" />

    <template v-else>
      <el-table :data="stages" size="small" v-loading="loading" style="width: 100%">
        <el-table-column prop="stage_order" label="序号" width="90" />
        <el-table-column prop="title" label="阶段名称" min-width="180" />
        <el-table-column label="起止时间" min-width="220">
          <template #default="{ row }">
            <span>{{ row.starts_at ? row.starts_at.slice(0, 10) : "" }}</span>
            <span> ~ </span>
            <span>{{ row.ends_at ? row.ends_at.slice(0, 10) : "" }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="grade" label="年级" width="100" />
        <el-table-column prop="description" label="说明" min-width="220" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="stages.length === 0 && !loading" description="" />
    </template>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑阶段' : '新增阶段'" width="620px">
      <el-form label-width="96px">
        <el-form-item label="阶段名称">
          <el-input v-model="form.title" placeholder="" />
        </el-form-item>
        <el-form-item label="阶段序号">
          <el-input-number v-model="form.stage_order" :min="1" :max="99" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.starts_at" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.ends_at" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.stage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.stage-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.stage-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
