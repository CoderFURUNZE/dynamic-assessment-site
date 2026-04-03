<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type AuditItem = {
  id: number;
  actor: string;
  role: string;
  action: string;
  detail: string;
  created_at: string;
};

const loading = ref(false);
const actor = ref("");
const action = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const items = ref<AuditItem[]>([]);

async function load() {
  loading.value = true;
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize.value),
    });
    if (actor.value.trim()) params.set("actor", actor.value.trim());
    if (action.value.trim()) params.set("action", action.value.trim());
    const res = await api.get(`/admin/audit?${params.toString()}`);
    items.value = res.data?.items ?? [];
    total.value = Number(res.data?.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载审计日志失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="audit-page">
    <section class="hero panel-card">
      <div>
        <p class="eyebrow">Audit Log</p>
        <h1>审计日志</h1>
        <p>用于回看管理员和教师的关键操作，便于联调定位和答辩说明平台治理能力。</p>
      </div>
      <div class="filters">
        <el-input v-model="actor" placeholder="操作人" style="width: 160px" />
        <el-input v-model="action" placeholder="动作关键字" style="width: 200px" />
        <el-button @click="page = 1; load()">查询</el-button>
      </div>
    </section>

    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-table :data="items" size="small">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 19) }}</template>
        </el-table-column>
        <el-table-column prop="actor" label="操作人" width="120" />
        <el-table-column prop="role" label="角色" width="100" />
        <el-table-column prop="action" label="动作" width="220" />
        <el-table-column prop="detail" label="详情" min-width="420" show-overflow-tooltip />
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, prev, pager, next"
          :total="total"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.audit-page { display: grid; gap: 20px; }
.hero { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.eyebrow { margin: 0 0 8px; font-size: 12px; font-weight: 800; color: #6b7d91; text-transform: uppercase; }
h1 { margin: 0; font-size: 28px; color: #1f2d3d; }
p { color: #62748a; line-height: 1.7; }
.filters { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
