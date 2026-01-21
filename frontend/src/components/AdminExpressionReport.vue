<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type UserRow = { id: number; username: string; role: string };
type KpRow = { id: number; code: string; title: string };

const users = ref<UserRow[]>([]);
const kps = ref<KpRow[]>([]);
const loading = ref(false);
const userId = ref<number | null>(null);
const kpId = ref<number | null>(null);
const days = ref(14);
const limit = ref(200);
const report = ref<any | null>(null);

const summary = computed(() => report.value ?? { total: 0, avg_confidence: 0, avg_difficulty: 0 });
const byLabel = computed(() => report.value?.by_label ?? []);
const daily = computed(() => report.value?.daily ?? []);
const items = computed(() => report.value?.items ?? []);

async function loadUsers() {
  const res = await api.get("/admin/users?page=1&page_size=200");
  users.value = (res.data.items ?? []).filter((u: any) => u.role === "student");
  if (!userId.value && users.value.length) userId.value = users.value[0].id;
}

async function loadKps() {
  const res = await api.get("/admin/kps?page=1&page_size=200");
  kps.value = res.data.items ?? [];
}

async function loadReport() {
  if (!userId.value) return;
  loading.value = true;
  try {
    const query = new URLSearchParams({
      user_id: String(userId.value),
      days: String(days.value),
      limit: String(limit.value),
    });
    if (kpId.value) query.set("kp_id", String(kpId.value));
    const res = await api.get(`/admin/expression/report?${query.toString()}`);
    report.value = res.data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载表情信号报表失败");
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await loadUsers();
  await loadKps();
  await loadReport();
});
</script>

<template>
  <el-card shadow="never">
    <template #header>表情/行为信号报表</template>
    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center">
      <el-select v-model="userId" filterable placeholder="选择学生" style="width: 200px" @change="loadReport">
        <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
      </el-select>
      <el-select v-model="kpId" filterable clearable placeholder="全部知识点" style="width: 260px" @change="loadReport">
        <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
      </el-select>
      <el-select v-model="days" style="width: 140px" @change="loadReport">
        <el-option label="近 7 天" :value="7" />
        <el-option label="近 14 天" :value="14" />
        <el-option label="近 30 天" :value="30" />
        <el-option label="近 90 天" :value="90" />
      </el-select>
      <el-select v-model="limit" style="width: 140px" @change="loadReport">
        <el-option label="记录 100 条" :value="100" />
        <el-option label="记录 200 条" :value="200" />
        <el-option label="记录 500 条" :value="500" />
      </el-select>
      <el-button size="small" type="primary" :loading="loading" @click="loadReport">刷新</el-button>
    </div>

    <div style="display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 12px">
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">采集次数</div>
        <div style="font-weight: 600; font-size: 20px">{{ summary.total }}</div>
      </el-card>
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">平均置信度</div>
        <div style="font-weight: 600; font-size: 20px">{{ summary.avg_confidence.toFixed(2) }}</div>
      </el-card>
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">平均困难度</div>
        <div style="font-weight: 600; font-size: 20px">{{ summary.avg_difficulty.toFixed(2) }}</div>
      </el-card>
    </div>

    <div style="margin-top: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">近 {{ days }} 天趋势</div>
      <div style="display: flex; gap: 6px; align-items: flex-end; height: 120px; margin-bottom: 6px">
        <div
          v-for="item in daily"
          :key="item.date"
          :title="`${item.date} 采集${item.total}次，均值难度${item.avg_difficulty.toFixed(2)}`"
          :style="{
            height: `${Math.max(6, Math.round((item.total || 0) * 4))}px`,
            width: '18px',
            background: '#6abf92',
            borderRadius: '6px',
          }"
        />
      </div>
      <el-table :data="daily" size="small" style="width: 100%" max-height="220">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="total" label="采集次数" width="120" />
        <el-table-column
          label="平均置信度"
          width="120"
          :formatter="(row: any) => (row.avg_confidence ?? 0).toFixed(2)"
        />
        <el-table-column
          label="平均困难度"
          width="120"
          :formatter="(row: any) => (row.avg_difficulty ?? 0).toFixed(2)"
        />
      </el-table>
    </div>

    <div style="margin-top: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">按标签统计</div>
      <el-table :data="byLabel" size="small" style="width: 100%" max-height="220">
        <el-table-column prop="label" label="标签" width="160" />
        <el-table-column prop="total" label="次数" width="100" />
        <el-table-column
          label="平均置信度"
          width="120"
          :formatter="(row: any) => (row.avg_confidence ?? 0).toFixed(2)"
        />
        <el-table-column
          label="平均困难度"
          width="120"
          :formatter="(row: any) => (row.avg_difficulty ?? 0).toFixed(2)"
        />
      </el-table>
    </div>

    <div style="margin-top: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">最近记录</div>
      <el-table :data="items" size="small" style="width: 100%" max-height="260">
        <el-table-column prop="created_at" label="时间" min-width="160" />
        <el-table-column prop="label" label="标签" width="140" />
        <el-table-column prop="confidence" label="置信度" width="100" />
        <el-table-column prop="difficulty" label="困难度" width="100" />
        <el-table-column prop="kp_id" label="知识点ID" width="100" />
      </el-table>
    </div>
  </el-card>
</template>
