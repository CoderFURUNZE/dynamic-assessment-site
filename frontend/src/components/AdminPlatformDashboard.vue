<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const loading = ref(false);
const stats = reactive({
  totalUsers: 0,
  totalTeachers: 0,
  totalStudents: 0,
  totalAdmins: 0,
  totalDimensions: 0,
  totalIndicators: 0,
});

async function load() {
  loading.value = true;
  try {
    const [usersAll, teachers, students, admins, dimensions] = await Promise.all([
      api.get("/admin/users?page=1&page_size=1"),
      api.get("/admin/users?page=1&page_size=1&role=teacher"),
      api.get("/admin/users?page=1&page_size=1&role=student"),
      api.get("/admin/users?page=1&page_size=1&role=admin"),
      api.get("/portrait/dimensions/tree"),
    ]);
    stats.totalUsers = Number(usersAll.data?.total ?? 0);
    stats.totalTeachers = Number(teachers.data?.total ?? 0);
    stats.totalStudents = Number(students.data?.total ?? 0);
    stats.totalAdmins = Number(admins.data?.total ?? 0);
    const dims = dimensions.data?.items ?? [];
    stats.totalDimensions = dims.length;
    stats.totalIndicators = dims.reduce((sum: number, item: any) => sum + Number(item?.indicators?.length ?? 0), 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载管理员仪表盘失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="dashboard-shell" v-loading="loading">
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="dashboard-header">
          <div>
            <div class="dashboard-title">平台治理概览</div>
            <div class="dashboard-sub">管理员只看平台级数据：账号、角色、指标和画像规则底座。</div>
          </div>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
        </div>
      </template>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-label">用户总数</div>
          <div class="metric-value">{{ stats.totalUsers }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">教师数量</div>
          <div class="metric-value">{{ stats.totalTeachers }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">学生数量</div>
          <div class="metric-value">{{ stats.totalStudents }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">管理员数量</div>
          <div class="metric-value">{{ stats.totalAdmins }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">一级指标数</div>
          <div class="metric-value">{{ stats.totalDimensions }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">二级指标数</div>
          <div class="metric-value">{{ stats.totalIndicators }}</div>
        </div>
      </div>
    </el-card>

    <el-card class="panel-card" shadow="never">
      <template #header>管理员操作建议</template>
      <ol class="todo-list">
        <li>先维护用户和老师账号状态（启用/禁用、角色、基础信息）。</li>
        <li>再维护指标池（一级维度和二级指标）。</li>
        <li>最后维护画像规则（阈值、权重、策略模板），供教师端按课程使用。</li>
      </ol>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard-shell {
  display: grid;
  gap: 16px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dashboard-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.dashboard-sub {
  margin-top: 4px;
  color: var(--app-ink-soft);
  font-size: 13px;
}

.metric-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.metric-card {
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: #fff;
  padding: 14px;
}

.metric-label {
  color: var(--app-ink-soft);
  font-size: 12px;
}

.metric-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
  color: var(--app-ink);
}

.todo-list {
  margin: 0;
  padding-left: 20px;
  color: var(--app-ink);
  display: grid;
  gap: 8px;
  line-height: 1.6;
}
</style>

