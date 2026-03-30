<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Reading, Refresh, Plus, Histogram } from "@element-plus/icons-vue";
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
  <div class="edu-page one-screen teacher-courses" v-loading="loading">
    <div class="teacher-courses__hero">
      <div class="teacher-courses__hero-inner">
        <div class="teacher-courses__hero-text">
          <p class="teacher-courses__eyebrow">教师工作台</p>
          <h1 class="teacher-courses__title">我的课程</h1>
          <p class="teacher-courses__subtitle">管理已开课课程，或从目录中激活新课程，进入图谱与资源建设。</p>
        </div>
        <el-button class="teacher-courses__refresh" round type="primary" plain @click="loadCatalog" :loading="loading">
          <el-icon class="el-icon--left"><Refresh /></el-icon>
          刷新列表
        </el-button>
      </div>
    </div>

    <section class="teacher-courses__stats" aria-label="课程统计">
      <div class="teacher-courses__stat teacher-courses__stat--on">
        <div class="teacher-courses__stat-icon" aria-hidden="true">
          <el-icon><Reading /></el-icon>
        </div>
        <div class="teacher-courses__stat-body">
          <span class="teacher-courses__stat-label">已激活</span>
          <strong class="teacher-courses__stat-value">{{ myCourses.length }}</strong>
        </div>
      </div>
      <div class="teacher-courses__stat teacher-courses__stat--pending">
        <div class="teacher-courses__stat-icon" aria-hidden="true">
          <el-icon><Plus /></el-icon>
        </div>
        <div class="teacher-courses__stat-body">
          <span class="teacher-courses__stat-label">可激活</span>
          <strong class="teacher-courses__stat-value">{{ availableRows.filter((item) => item.can_activate).length }}</strong>
        </div>
      </div>
      <div class="teacher-courses__stat teacher-courses__stat--hold">
        <div class="teacher-courses__stat-icon" aria-hidden="true">
          <el-icon><Histogram /></el-icon>
        </div>
        <div class="teacher-courses__stat-body">
          <span class="teacher-courses__stat-label">暂不可用</span>
          <strong class="teacher-courses__stat-value">{{ disabledRows.length }}</strong>
        </div>
      </div>
    </section>

    <div class="teacher-courses__columns main-layout-content">
      <section class="teacher-courses__panel teacher-courses__panel--active">
        <header class="teacher-courses__panel-head">
          <div class="teacher-courses__panel-title-wrap">
            <span class="teacher-courses__panel-dot teacher-courses__panel-dot--success" />
            <h2 class="teacher-courses__panel-title">已激活课程</h2>
          </div>
          <span class="teacher-courses__panel-badge">{{ myCourses.length }} 门</span>
        </header>

        <div v-if="myCourses.length" class="course-list-scroll">
          <div class="course-list">
            <article v-for="row in myCourses" :key="`mine-${row.id}`" class="course-card">
              <div class="course-card__top">
                <span class="course-card__code">{{ row.code }}</span>
                <h3 class="course-card__title">{{ row.title }}</h3>
              </div>
              <p class="course-card__desc">{{ row.description || "管理员暂未填写课程简介。" }}</p>
              <div class="course-card__chips">
                <span class="course-chip">{{ lifecycleLabel(row.lifecycle_status) }}</span>
                <span class="course-chip course-chip--muted">{{ row.target_class || "班级未绑定" }}</span>
              </div>
              <div class="course-card__actions">
                <el-button type="primary" round @click="openCourseWorkspace(row)">进入图谱工作区</el-button>
                <el-button round @click="openCourseStages(row)">阶段评价</el-button>
              </div>
            </article>
          </div>
        </div>
        <el-empty v-else class="teacher-courses__empty" description="暂无已激活课程">
          <template #image>
            <div class="teacher-courses__empty-icon">📚</div>
          </template>
        </el-empty>
      </section>

      <section class="teacher-courses__panel teacher-courses__panel--catalog">
        <header class="teacher-courses__panel-head">
          <div class="teacher-courses__panel-title-wrap">
            <span class="teacher-courses__panel-dot teacher-courses__panel-dot--info" />
            <h2 class="teacher-courses__panel-title">可激活课程</h2>
          </div>
          <span class="teacher-courses__panel-badge teacher-courses__panel-badge--info">{{ availableRows.length }} 门</span>
        </header>

        <div v-if="availableRows.length" class="course-list-scroll">
          <div class="course-list">
            <article v-for="row in availableRows" :key="`available-${row.id}`" class="course-card course-card--catalog">
              <div class="course-card__top">
                <span class="course-card__code">{{ row.code }}</span>
                <h3 class="course-card__title">{{ row.title }}</h3>
              </div>
              <p class="course-card__desc">{{ row.description || "管理员暂未填写课程简介。" }}</p>
              <div class="course-card__chips">
                <span class="course-chip" :class="row.can_activate ? 'course-chip--ok' : 'course-chip--warn'">
                  {{ row.can_activate ? "可激活" : "待管理员配置" }}
                </span>
              </div>
              <div class="course-card__actions">
                <el-button
                  type="primary"
                  round
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
        <el-empty v-else class="teacher-courses__empty" description="管理员暂未分配可激活课程">
          <template #image>
            <div class="teacher-courses__empty-icon">📋</div>
          </template>
        </el-empty>
      </section>
    </div>
  </div>
</template>

<style scoped>
.one-screen.teacher-courses {
  flex: 1 0 auto;
  display: flex;
  flex-direction: column;
  overflow: visible;
  gap: 0;
  max-width: 1280px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.teacher-courses__hero {
  margin-bottom: 22px;
  padding: 28px 28px 26px;
  border-radius: var(--app-radius-lg);
  background: linear-gradient(135deg, #eef4ff 0%, #f0fdf9 48%, #f8fafc 100%);
  border: 1px solid color-mix(in srgb, var(--app-primary) 12%, var(--app-border));
  box-shadow: var(--app-shadow-soft);
}

.teacher-courses__hero-inner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.teacher-courses__eyebrow {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--app-primary-deep);
  opacity: 0.85;
}

.teacher-courses__title {
  margin: 0 0 10px;
  font-size: clamp(26px, 4vw, 32px);
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--app-text-main);
  line-height: 1.2;
}

.teacher-courses__subtitle {
  margin: 0;
  max-width: 52ch;
  font-size: 14px;
  line-height: 1.65;
  color: var(--app-text-soft);
}

.teacher-courses__refresh {
  flex-shrink: 0;
  padding: 12px 22px;
  font-weight: 700;
  border-width: 1.5px;
}

.teacher-courses__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}

.teacher-courses__stat {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: var(--app-radius);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
  transition: border-color var(--app-duration) var(--app-ease-out), box-shadow var(--app-duration) var(--app-ease-out);
}

.teacher-courses__stat:hover {
  border-color: color-mix(in srgb, var(--app-primary) 28%, var(--app-border));
  box-shadow: var(--app-shadow);
}

.teacher-courses__stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 20px;
  color: #fff;
}

.teacher-courses__stat--on .teacher-courses__stat-icon {
  background: linear-gradient(145deg, #3b82f6 0%, #10b981 100%);
}

.teacher-courses__stat--pending .teacher-courses__stat-icon {
  background: linear-gradient(145deg, #6366f1 0%, #4f8cff 100%);
}

.teacher-courses__stat--hold .teacher-courses__stat-icon {
  background: linear-gradient(145deg, #94a3b8 0%, #cbd5e1 100%);
}

.teacher-courses__stat-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--app-text-soft);
  margin-bottom: 2px;
}

.teacher-courses__stat-value {
  font-size: 26px;
  font-weight: 800;
  color: var(--app-text-main);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.main-layout-content {
  flex: 1;
}

.teacher-courses__columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  align-items: start;
}

.teacher-courses__panel {
  border-radius: var(--app-radius-lg);
  background: var(--app-card);
  border: 1px solid color-mix(in srgb, var(--app-border) 90%, transparent);
  box-shadow: var(--app-shadow-soft);
  overflow: hidden;
  min-height: 200px;
}

.teacher-courses__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--app-border);
  background: linear-gradient(180deg, #fafcff 0%, #ffffff 100%);
}

.teacher-courses__panel-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.teacher-courses__panel-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex-shrink: 0;
}

.teacher-courses__panel-dot--success {
  background: linear-gradient(180deg, #34d399 0%, #10b981 100%);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.teacher-courses__panel-dot--info {
  background: linear-gradient(180deg, #93c5fd 0%, #3b82f6 100%);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
}

.teacher-courses__panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--app-text-main);
}

.teacher-courses__panel-badge {
  flex-shrink: 0;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.teacher-courses__panel-badge--info {
  background: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  border-color: rgba(59, 130, 246, 0.22);
}

.course-list-scroll {
  padding: 18px 20px 22px;
}

.course-list {
  display: grid;
  gap: 14px;
}

.course-card {
  padding: 18px 18px 16px;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: border-color var(--app-duration) var(--app-ease-out), box-shadow var(--app-duration) var(--app-ease-out),
    transform var(--app-duration) var(--app-ease-out);
}

.course-card:hover {
  border-color: color-mix(in srgb, var(--app-primary) 25%, var(--app-border));
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.07);
  transform: translateY(-1px);
}

.course-card--catalog {
  background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
}

.course-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px 12px;
  margin-bottom: 8px;
}

.course-card__code {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--app-primary-deep);
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--app-primary-soft);
  border: 1px solid color-mix(in srgb, var(--app-primary) 22%, transparent);
}

.course-card__title {
  margin: 0;
  flex: 1 1 auto;
  min-width: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--app-text-main);
  line-height: 1.35;
}

.course-card__desc {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--app-text-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.course-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.course-chip {
  font-size: 12px;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.course-chip--muted {
  font-weight: 500;
  color: #64748b;
}

.course-chip--ok {
  background: rgba(16, 185, 129, 0.1);
  color: #047857;
  border-color: rgba(16, 185, 129, 0.28);
}

.course-chip--warn {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
  border-color: rgba(245, 158, 11, 0.35);
}

.course-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.course-card__actions :deep(.el-button) {
  font-weight: 700;
}

.teacher-courses__empty {
  padding: 28px 16px 36px;
}

.teacher-courses__empty :deep(.el-empty__description) {
  margin-top: 12px;
  color: var(--app-text-soft);
  font-size: 14px;
}

.teacher-courses__empty-icon {
  font-size: 48px;
  line-height: 1;
  opacity: 0.85;
}

@media (max-width: 900px) {
  .teacher-courses__columns {
    grid-template-columns: 1fr;
  }

  .teacher-courses__stats {
    grid-template-columns: 1fr;
  }

  .teacher-courses__hero {
    padding: 22px 18px;
  }
}

@media (max-height: 800px) {
  .teacher-courses__subtitle {
    display: none;
  }

  .teacher-courses__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .teacher-courses__stats {
    grid-template-columns: 1fr;
  }
}
</style>
