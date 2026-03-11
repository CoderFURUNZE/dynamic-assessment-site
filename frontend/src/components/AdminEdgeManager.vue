<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type KP = { id: number; code: string; title: string };
type EdgeRow = { id: number; prereq_id: number; next_id: number; relation_type: string };

const props = defineProps<{ subject: string; grade: string }>();

const loading = ref(false);
const kps = ref<KP[]>([]);
const edges = ref<EdgeRow[]>([]);
const page = ref(1);
const pageSize = 15;
const total = ref(0);

const prereqId = ref<number | null>(null);
const nextId = ref<number | null>(null);
const relationType = ref("prerequisite");

const kpMap = computed(() => {
  const m = new Map<number, KP>();
  for (const kp of kps.value) m.set(kp.id, kp);
  return m;
});

async function loadKps() {
  const res = await api.get(`/graph/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
  kps.value = res.data;
  if (!prereqId.value && kps.value.length) prereqId.value = kps.value[0].id;
  if (!nextId.value && kps.value.length > 1) nextId.value = kps.value[1].id;
}

async function loadEdges() {
  loading.value = true;
  try {
    const res = await api.get(
      `/admin/edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&page=${page.value}&page_size=${pageSize}`
    );
    edges.value = res.data.items ?? [];
    total.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识边失败");
  } finally {
    loading.value = false;
  }
}

async function addEdge() {
  if (!prereqId.value || !nextId.value) return;
  if (prereqId.value === nextId.value) {
    ElMessage.warning("不能把同一个知识点作为前置与后继");
    return;
  }
  try {
    await api.post("/admin/edges", {
      subject: props.subject,
      grade: props.grade,
      prereq_id: prereqId.value,
      next_id: nextId.value,
      relation_type: relationType.value,
    });
    ElMessage.success("已添加");
    await loadEdges();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "添加失败");
  }
}

async function removeEdge(row: EdgeRow) {
  try {
    await api.delete(`/admin/edges/${row.id}`);
    ElMessage.success("已删除");
    await loadEdges();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败");
  }
}

watch(
  () => [props.subject, props.grade],
  async () => {
    await loadKps();
    page.value = 1;
    await loadEdges();
  },
  { immediate: true }
);

onMounted(async () => {
  await loadKps();
  await loadEdges();
});
</script>

<template>
  <el-card class="panel-card" shadow="never">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>知识边管理</div>
        <el-button @click="loadEdges" :loading="loading">刷新</el-button>
      </div>
    </template>

    <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap">
      <el-select v-model="prereqId" filterable style="width: 30%" placeholder="起点知识点">
        <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
      </el-select>
      <el-select v-model="relationType" style="width: 18%">
        <el-option label="前置关系" value="prerequisite" />
        <el-option label="关联关系" value="related" />
      </el-select>
      <el-select v-model="nextId" filterable style="width: 30%" placeholder="目标知识点">
        <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
      </el-select>
      <el-button type="primary" @click="addEdge">添加</el-button>
    </div>

    <el-table :data="edges" size="small" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="起点">
        <template #default="{ row }">
          {{ kpMap.get(row.prereq_id)?.code ?? row.prereq_id }} {{ kpMap.get(row.prereq_id)?.title ?? "" }}
        </template>
      </el-table-column>
      <el-table-column label="关系" width="110">
        <template #default="{ row }">
          <el-tag :type="row.relation_type === 'prerequisite' ? 'primary' : 'success'">
            {{ row.relation_type === "prerequisite" ? "前置" : "关联" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标">
        <template #default="{ row }">
          {{ kpMap.get(row.next_id)?.code ?? row.next_id }} {{ kpMap.get(row.next_id)?.title ?? "" }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="removeEdge(row)">删除</el-button>
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
        @current-change="loadEdges"
      />
    </div>
  </el-card>
</template>
