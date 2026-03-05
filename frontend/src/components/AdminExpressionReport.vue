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

const labels = {
  header: "\u8868\u60c5/\u884c\u4e3a\u4fe1\u53f7\u62a5\u8868",
  chooseStudent: "\u9009\u62e9\u5b66\u751f",
  allKp: "\u5168\u90e8\u77e5\u8bc6\u70b9",
  recent7: "\u8fd1 7 \u5929",
  recent14: "\u8fd1 14 \u5929",
  recent30: "\u8fd1 30 \u5929",
  recent90: "\u8fd1 90 \u5929",
  records100: "\u8bb0\u5f55 100 \u6761",
  records200: "\u8bb0\u5f55 200 \u6761",
  records500: "\u8bb0\u5f55 500 \u6761",
  refresh: "\u5237\u65b0",
  statTotal: "\u91c7\u96c6\u6b21\u6570",
  statAvgConfidence: "\u5e73\u5747\u7f6e\u4fe1\u5ea6",
  statAvgDifficulty: "\u5e73\u5747\u56f0\u96be\u5ea6",
  trendPrefix: "\u8fd1 ",
  trendSuffix: " \u5929\u8d8b\u52bf",
  labelStats: "\u6309\u6807\u7b7e\u7edf\u8ba1",
  recentRecords: "\u6700\u8fd1\u8bb0\u5f55",
  date: "\u65e5\u671f",
  total: "\u91c7\u96c6\u6b21\u6570",
  avgConfidence: "\u5e73\u5747\u7f6e\u4fe1\u5ea6",
  avgDifficulty: "\u5e73\u5747\u56f0\u96be\u5ea6",
  tag: "\u6807\u7b7e",
  times: "\u6b21\u6570",
  time: "\u65f6\u95f4",
  confidence: "\u7f6e\u4fe1\u5ea6",
  difficulty: "\u56f0\u96be\u5ea6",
  kpId: "\u77e5\u8bc6\u70b9ID",
  errorLoad: "\u52a0\u8f7d\u8868\u60c5\u4fe1\u53f7\u62a5\u8868\u5931\u8d25",
};

const summary = computed(() => report.value ?? { total: 0, avg_confidence: 0, avg_difficulty: 0 });
const byLabel = computed(() => report.value?.by_label ?? []);
const daily = computed(() => report.value?.daily ?? []);
const items = computed(() => report.value?.items ?? []);
const trendTitle = computed(() => `${labels.trendPrefix}${days.value}${labels.trendSuffix}`);
const maxDailyTotal = computed(() => {
  if (!daily.value.length) return 1;
  return Math.max(1, ...daily.value.map((d: any) => Number(d.total ?? 0)));
});

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
    ElMessage.error(e?.response?.data?.detail ?? labels.errorLoad);
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
    <template #header>{{ labels.header }}</template>

    <div class="expr-toolbar">
      <el-select v-model="userId" filterable :placeholder="labels.chooseStudent" style="width: 200px" @change="loadReport">
        <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
      </el-select>
      <el-select v-model="kpId" filterable clearable :placeholder="labels.allKp" style="width: 260px" @change="loadReport">
        <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
      </el-select>
      <el-select v-model="days" style="width: 140px" @change="loadReport">
        <el-option :label="labels.recent7" :value="7" />
        <el-option :label="labels.recent14" :value="14" />
        <el-option :label="labels.recent30" :value="30" />
        <el-option :label="labels.recent90" :value="90" />
      </el-select>
      <el-select v-model="limit" style="width: 140px" @change="loadReport">
        <el-option :label="labels.records100" :value="100" />
        <el-option :label="labels.records200" :value="200" />
        <el-option :label="labels.records500" :value="500" />
      </el-select>
      <el-button size="small" type="primary" :loading="loading" @click="loadReport">{{ labels.refresh }}</el-button>
    </div>

    <div class="expr-stats">
      <div class="expr-stat">
        <div class="expr-stat__label">{{ labels.statTotal }}</div>
        <div class="expr-stat__value">{{ summary.total }}</div>
      </div>
      <div class="expr-stat">
        <div class="expr-stat__label">{{ labels.statAvgConfidence }}</div>
        <div class="expr-stat__value">{{ summary.avg_confidence.toFixed(2) }}</div>
      </div>
      <div class="expr-stat">
        <div class="expr-stat__label">{{ labels.statAvgDifficulty }}</div>
        <div class="expr-stat__value">{{ summary.avg_difficulty.toFixed(2) }}</div>
      </div>
    </div>

    <div class="expr-section">
      <div class="expr-section__title">{{ trendTitle }}</div>
      <div class="expr-bars">
        <div
          v-for="item in daily"
          :key="item.date"
          class="expr-bar"
          :title="`${item.date} ${labels.statTotal} ${item.total} ${labels.statAvgDifficulty} ${item.avg_difficulty.toFixed(2)}`"
          :style="{ height: `${Math.max(6, Math.round(((item.total || 0) / maxDailyTotal) * 96))}px` }"
        />
      </div>
      <el-table :data="daily" size="small" style="width: 100%" max-height="220">
        <el-table-column prop="date" :label="labels.date" width="120" />
        <el-table-column prop="total" :label="labels.total" width="120" />
        <el-table-column
          :label="labels.avgConfidence"
          width="120"
          :formatter="(row: any) => (row.avg_confidence ?? 0).toFixed(2)"
        />
        <el-table-column
          :label="labels.avgDifficulty"
          width="120"
          :formatter="(row: any) => (row.avg_difficulty ?? 0).toFixed(2)"
        />
      </el-table>
    </div>

    <div class="expr-section">
      <div class="expr-section__title">{{ labels.labelStats }}</div>
      <el-table :data="byLabel" size="small" style="width: 100%" max-height="220">
        <el-table-column prop="label" :label="labels.tag" width="160" />
        <el-table-column prop="total" :label="labels.times" width="100" />
        <el-table-column
          :label="labels.avgConfidence"
          width="120"
          :formatter="(row: any) => (row.avg_confidence ?? 0).toFixed(2)"
        />
        <el-table-column
          :label="labels.avgDifficulty"
          width="120"
          :formatter="(row: any) => (row.avg_difficulty ?? 0).toFixed(2)"
        />
      </el-table>
    </div>

    <div class="expr-section">
      <div class="expr-section__title">{{ labels.recentRecords }}</div>
      <el-table :data="items" size="small" style="width: 100%" max-height="260">
        <el-table-column prop="created_at" :label="labels.time" min-width="160" />
        <el-table-column prop="label" :label="labels.tag" width="140" />
        <el-table-column prop="confidence" :label="labels.confidence" width="100" />
        <el-table-column prop="difficulty" :label="labels.difficulty" width="100" />
        <el-table-column prop="kp_id" :label="labels.kpId" width="100" />
      </el-table>
    </div>
  </el-card>
</template>
