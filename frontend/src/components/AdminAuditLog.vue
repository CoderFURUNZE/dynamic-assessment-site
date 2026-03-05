<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const loading = ref(false);
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const actor = ref("");
const action = ref("");

async function load() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    params.set("page", String(page.value));
    params.set("page_size", String(pageSize));
    if (actor.value.trim()) params.set("actor", actor.value.trim());
    if (action.value.trim()) params.set("action", action.value.trim());
    const res = await api.get(`/admin/audit?${params.toString()}`);
    items.value = res.data.items ?? [];
    total.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载操作日志失败");
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  actor.value = "";
  action.value = "";
  page.value = 1;
  load();
}

onMounted(load);
</script>

<template>
  <el-card class="panel-card" shadow="never">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>操作日志</div>
        <el-button size="small" @click="load" :loading="loading">刷新</el-button>
      </div>
    </template>

    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px">
      <el-input v-model="actor" placeholder="操作者" style="width: 200px" />
      <el-input v-model="action" placeholder="动作包含" style="width: 220px" />
      <el-button type="primary" size="small" @click="load">查询</el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
    </div>

    <el-table :data="items" v-loading="loading" style="width: 100%">
      <el-table-column prop="created_at" label="时间" width="190" />
      <el-table-column prop="actor" label="操作者" width="120" />
      <el-table-column prop="role" label="角色" width="110" />
      <el-table-column prop="action" label="动作" width="180" />
      <el-table-column prop="detail" label="详情" />
    </el-table>

    <div style="display: flex; justify-content: flex-end; margin-top: 12px">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="total"
        v-model:current-page="page"
        @current-change="load"
      />
    </div>
  </el-card>
</template>
