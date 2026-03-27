<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { saveTeacherSubject } from "../utils/teacherCourse";

type CourseRow = {
  id: number;
  code: string;
  title: string;
  description: string;
  active: boolean;
  lifecycle_status?: string;
  target_class?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  archived_at?: string | null;
  teacher_id?: number | null;
  teacher_name?: string;
  max_students?: number;
  apply_deadline?: string | null;
  enroll_status?: string;
  activated?: boolean;
  can_activate?: boolean;
  activation_status?: string;
};

const router = useRouter();
const loading = ref(false);
const activatingId = ref<number | null>(null);
const catalogRows = ref<CourseRow[]>([]);

const myCourses = computed(() => catalogRows.value.filter((item) => item.activated));
const availableRows = computed(() => catalogRows.value.filter((item) => !item.activated));
const disabledRows = computed(() => availableRows.value.filter((item) => !item.can_activate));

function enrollStatusLabel(value?: string) {
  const normalized = String(value || "open").toLowerCase();
  if (normalized === "open") return "开放报名";
  if (normalized === "full") return "名额已满";
  if (normalized === "closed") return "关闭报名";
  if (normalized === "expired") return "已截止";
  return normalized;
}

function courseStatusText(row: CourseRow) {
  if (row.activated) return "你已激活";
  if (!row.active) return "管理员未启用";
  if (row.lifecycle_status === "draft") return "还未开课";
  if (row.lifecycle_status === "archived") return "课程已归档";
  if (row.can_activate) return "可以激活";
  return row.activation_status || "暂时不可激活";
}

function lifecycleLabel(value?: string) {
  const normalized = String(value || "draft").toLowerCase();
  if (normalized === "active") return "开课中";
  if (normalized === "archived") return "已归档";
  return "待开课";
}

async function loadCatalog() {
  loading.value = true;
  try {
    const res = await api.get("/graph/teacher/course-catalog");
    catalogRows.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程列表失败");
    catalogRows.value = [];
  } finally {
    loading.value = false;
  }
}

async function activateCourse(row: CourseRow) {
  if (activatingId.value) return;
  activatingId.value = row.id;
  try {
    await api.post(`/graph/teacher/courses/${row.id}/activate`);
    ElMessage.success("课程已激活，现在可以去建立图谱和资源");
    await loadCatalog();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "激活课程失败");
  } finally {
    activatingId.value = null;
  }
}

function openCourseWorkspace(row: CourseRow) {
  saveTeacherSubject(row.title);
  router.push({ path: "/teacher/graph-workspace", query: { subject: row.title } });
}

function openCourseStages(row: CourseRow) {
  saveTeacherSubject(row.title);
  router.push({ path: "/teacher/stages", query: { subject: row.title } });
}

onMounted(loadCatalog);
</script>

<template>
  <div class="edu-page one-screen" v-loading="loading">
    <header class="edu-header compact">
      <div class="edu-header__left">
        <h1 class="edu-header__title">我的课程</h1>
        <p class="edu-header__desc">管理和激活您负责的教学课程，建立知识图谱与教学资源。</p>
      </div>
      <div class="edu-header__actions">
        <el-button type="primary" plain @click="loadCatalog" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新列表
        </el-button>
      </div>
    </header>

    <section class="edu-stats-grid compact">
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">已激活课程</span>
        <strong class="edu-stat-card__value">{{ myCourses.length }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">待激活课程</span>
        <strong class="edu-stat-card__value">{{ availableRows.filter(item => item.can_activate).length }}</strong>
      </div>
      <div class="edu-stat-card">
        <span class="edu-stat-card__label">暂不可用</span>
        <strong class="edu-stat-card__value">{{ disabledRows.length }}</strong>
      </div>
    </section>

    <div class="edu-grid-2 main-layout-content">
      <section class="edu-panel flex-panel">
        <header class="edu-panel__header">
          <h2 class="edu-panel__title">已激活课程</h2>
          <el-tag round type="success">{{ myCourses.length }} 门</el-tag>
        </header>

        <div v-if="myCourses.length" class="course-list-scroll">
          <div class="course-list">
            <article v-for="row in myCourses" :key="`mine-${row.id}`" class="edu-course-card">
              <span class="edu-course-card__tag">{{ row.code }}</span>
              <h3 class="course-title">{{ row.title }}</h3>
              <p class="course-desc">{{ row.description || "管理员暂未填写课程简介。" }}</p>
              
              <div class="course-meta">
                <div class="meta-item"><span>状态</span> {{ lifecycleLabel(row.lifecycle_status) }}</div>
                <div class="meta-item"><span>班级</span> {{ row.target_class || "未绑定" }}</div>
              </div>

              <div class="course-actions">
                <el-button type="primary" @click="openCourseWorkspace(row)">工作区</el-button>
                <el-button plain @click="openCourseStages(row)">阶段</el-button>
              </div>
            </article>
          </div>
        </div>
        <el-empty v-else description="暂无已激活课程" />
      </section>

      <section class="edu-panel flex-panel">
        <header class="edu-panel__header">
          <h2 class="edu-panel__title">可激活课程</h2>
          <el-tag round type="info">{{ availableRows.length }} 门</el-tag>
        </header>

        <div v-if="availableRows.length" class="course-list-scroll">
          <div class="course-list">
            <article v-for="row in availableRows" :key="`available-${row.id}`" class="edu-course-card available">
              <span class="edu-course-card__tag">{{ row.code }}</span>
              <h3 class="course-title">{{ row.title }}</h3>
              <p class="course-desc">{{ row.description || "管理员暂未填写课程简介。" }}</p>
              
              <div class="course-meta">
                <div class="meta-item"><span>权限</span> {{ row.can_activate ? '可激活' : '待配置' }}</div>
              </div>

              <div class="course-actions">
                <el-button 
                  type="primary" 
                  plain
                  :disabled="!row.can_activate" 
                  :loading="activatingId === row.id" 
                  @click="activateCourse(row)"
                >
                  激活课程
                </el-button>
              </div>
            </article>
          </div>
        </div>
        <el-empty v-else description="暂无可激活课程" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.one-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.edu-header.compact {
  margin-bottom: 16px;
  padding: 12px 0;
}

.edu-stats-grid.compact {
  margin-bottom: 16px;
  gap: 16px;
}

.edu-stat-card {
  padding: 12px 20px;
}

.edu-stat-card__value {
  font-size: 24px;
}

.main-layout-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-height: 0;
}

.flex-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 20px;
}

.course-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.course-list {
  display: grid;
  gap: 12px;
}

.edu-course-card {
  padding: 16px;
}

.course-title {
  font-size: 16px;
  margin-bottom: 4px;
}

.course-desc {
  font-size: 12px;
  margin-bottom: 12px;
  -webkit-line-clamp: 1;
}

.course-meta {
  margin-bottom: 12px;
  padding: 8px;
  gap: 12px;
}

.meta-item {
  font-size: 11px;
}

.course-actions .el-button {
  padding: 8px 12px;
  font-size: 13px;
}

@media (max-height: 800px) {
  .edu-header__desc { display: none; }
  .edu-stats-grid { display: none; }
}
</style>
