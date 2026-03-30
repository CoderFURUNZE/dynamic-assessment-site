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
    <div class="edu-stats-grid">
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">用户总数</span>
        <strong class="edu-stat-card__value">{{ stats.totalUsers }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">教师数量</span>
        <strong class="edu-stat-card__value">{{ stats.totalTeachers }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">学生数量</span>
        <strong class="edu-stat-card__value">{{ stats.totalStudents }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">管理员数量</span>
        <strong class="edu-stat-card__value">{{ stats.totalAdmins }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">一级指标数</span>
        <strong class="edu-stat-card__value">{{ stats.totalDimensions }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">二级指标数</span>
        <strong class="edu-stat-card__value">{{ stats.totalIndicators }}</strong>
      </div>
    </div>

    <section class="edu-panel">
      <header class="edu-panel__header">
        <h2 class="edu-panel__title">管理员操作建议</h2>
      </header>
      <div class="todo-content">
        <div class="todo-item">
          <div class="todo-index">1</div>
          <div class="todo-text">
            <strong>维护账号状态</strong>
            <span>管理用户和老师账号的基础信息、角色及启用/禁用状态。</span>
          </div>
        </div>
        <div class="todo-item">
          <div class="todo-index">2</div>
          <div class="todo-text">
            <strong>维护指标池</strong>
            <span>定义系统核心的一级维度和二级指标，这是画像生成的底座。</span>
          </div>
        </div>
        <div class="todo-item">
          <div class="todo-index">3</div>
          <div class="todo-text">
            <strong>配置画像规则</strong>
            <span>设置阈值、权重及策略模板，供教师端在具体课程中应用。</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard-shell {
  display: grid;
  gap: 24px;
}

.todo-content {
  display: grid;
  gap: 16px;
}

.todo-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--app-surface-muted);
  border-radius: 16px;
  align-items: center;
  border: 1px solid color-mix(in srgb, var(--app-border) 75%, #ffffff);
}

.todo-index {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--app-gradient-primary);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 800;
  flex-shrink: 0;
}

.todo-text {
  display: flex;
  flex-direction: column;
}

.todo-text strong {
  font-size: 15px;
  color: var(--app-text-main);
}

.todo-text span {
  font-size: 13px;
  color: var(--app-text-soft);
}
</style>

