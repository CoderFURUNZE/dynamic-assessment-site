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
const report = ref<any | null>(null);

const summary = computed(() => report.value ?? { total: 0, correct: 0, incorrect: 0, accuracy: 0 });
const daily = computed(() => report.value?.daily ?? []);
const byKp = computed(() => report.value?.by_kp ?? []);

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
    });
    if (kpId.value) query.set("kp_id", String(kpId.value));
    const res = await api.get(`/admin/practice/report?${query.toString()}`);
    report.value = res.data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载练习报表失败");
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
    <template #header>学生练习报表</template>
    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center">
      <el-select v-model="userId" filterable placeholder="选择学生" style="width: 200px" @change="loadReport">
        <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
      </el-select>
      <el-select v-model="kpId" filterable clearable placeholder="全部知识点" style="width: 260px" @change="loadReport">
        <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
      </el-select>
      <el-select v-model="days" style="width: 140px" @change="loadReport">
        <el-option label="近7天" :value="7" />
        <el-option label="近14天" :value="14" />
        <el-option label="近30天" :value="30" />
        <el-option label="近90天" :value="90" />
      </el-select>
      <el-button size="small" type="primary" :loading="loading" @click="loadReport">刷新</el-button>
    </div>

    <div style="display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 12px">
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">总作答</div>
        <div style="font-weight: 600; font-size: 20px">{{ summary.total }}</div>
      </el-card>
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">正确</div>
        <div style="font-weight: 600; font-size: 20px">{{ summary.correct }}</div>
      </el-card>
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">错误</div>
        <div style="font-weight: 600; font-size: 20px">{{ summary.incorrect }}</div>
      </el-card>
      <el-card shadow="never">
        <div style="font-size: 12px; color: #666">正确率</div>
        <div style="font-weight: 600; font-size: 20px">{{ Math.round((summary.accuracy || 0) * 100) }}%</div>
      </el-card>
    </div>

    <div style="margin-top: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">近 {{ days }} 天趋势</div>
      <div style="display: flex; gap: 6px; align-items: flex-end; height: 120px; margin-bottom: 6px">
        <div
          v-for="item in daily"
          :key="item.date"
          :title="`${item.date} 正确率 ${Math.round((item.accuracy || 0) * 100)}%`"
          :style="{
            height: `${Math.max(6, Math.round((item.accuracy || 0) * 100))}%`,
            width: '18px',
            background: '#5fbf7a',
            borderRadius: '6px',
          }"
        />
      </div>
      <el-table :data="daily" size="small" style="width: 100%" max-height="220">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="total" label="作答数" width="100" />
        <el-table-column prop="correct" label="正确数" width="100" />
        <el-table-column
          label="正确率"
          width="100"
          :formatter="(row: any) => `${Math.round((row.accuracy || 0) * 100)}%`"
        />
      </el-table>
    </div>

    <div style="margin-top: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">按知识点统计</div>
      <el-table :data="byKp" size="small" style="width: 100%" max-height="260">
        <el-table-column prop="kp_code" label="知识点编码" width="140" />
        <el-table-column prop="kp_title" label="知识点" />
        <el-table-column prop="total" label="作答数" width="100" />
        <el-table-column prop="correct" label="正确数" width="100" />
        <el-table-column
          label="正确率"
          width="100"
          :formatter="(row: any) => `${Math.round((row.accuracy || 0) * 100)}%`"
        />
      </el-table>
    </div>
  </el-card>
</template>
