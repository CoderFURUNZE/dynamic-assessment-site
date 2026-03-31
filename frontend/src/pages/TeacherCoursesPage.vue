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
  activated?: boolean;
  can_activate?: boolean;
};

const router = useRouter();
const loading = ref(false);
const activatingId = ref<number | null>(null);
const catalogRows = ref<CourseRow[]>([]);

const myCourses = computed(() => catalogRows.value.filter((item) => item.activated));
const availableRows = computed(() => catalogRows.value.filter((item) => !item.activated));
const disabledRows = computed(() => availableRows.value.filter((item) => !item.can_activate));
const primaryCourse = computed(() => myCourses.value[0] ?? null);

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
    ElMessage.success("课程已激活，现在可以去建设图谱和资源");
    await loadCatalog();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "激活课程失败");
  } finally {
    activatingId.value = null;
  }
}

function openCourseWorkspace(row: CourseRow) {
  saveTeacherSubject(row.title);
  router.push({ path: "/teacher/content", query: { subject: row.title } });
}

function openCourseStages(row: CourseRow) {
  saveTeacherSubject(row.title);
  router.push({ path: "/teacher/evaluation", query: { subject: row.title, tab: "stages" } });
}

onMounted(loadCatalog);
</script>

<template>
  <div class="teacher-courses-page" v-loading="loading">
    <section class="teacher-courses-page__hero">
      <div class="teacher-courses-page__hero-copy">
        <span class="teacher-courses-page__eyebrow">课程工作台</span>
        <h1>先确定当前课程，再进入图谱和评价工作区</h1>
        <p>首页只保留课程概览和关键动作，图谱编辑、阶段评价、学生分析都进入各自独立页面处理。</p>
      </div>
      <div class="teacher-courses-page__hero-actions">
        <el-button type="primary" plain round @click="loadCatalog" :loading="loading">
          <el-icon class="el-icon--left"><Refresh /></el-icon>
          刷新课程
        </el-button>
        <el-button v-if="primaryCourse" type="primary" round @click="openCourseWorkspace(primaryCourse)">进入知识图谱</el-button>
      </div>
    </section>

    <section class="teacher-courses-page__stats">
      <article class="teacher-courses-page__stat-card">
        <div class="teacher-courses-page__stat-icon teacher-courses-page__stat-icon--on"><el-icon><Reading /></el-icon></div>
        <div>
          <span>已激活</span>
          <strong>{{ myCourses.length }}</strong>
        </div>
      </article>
      <article class="teacher-courses-page__stat-card">
        <div class="teacher-courses-page__stat-icon teacher-courses-page__stat-icon--pending"><el-icon><Plus /></el-icon></div>
        <div>
          <span>可激活</span>
          <strong>{{ availableRows.filter((item) => item.can_activate).length }}</strong>
        </div>
      </article>
      <article class="teacher-courses-page__stat-card">
        <div class="teacher-courses-page__stat-icon teacher-courses-page__stat-icon--hold"><el-icon><Histogram /></el-icon></div>
        <div>
          <span>暂不可用</span>
          <strong>{{ disabledRows.length }}</strong>
        </div>
      </article>
    </section>

    <section class="teacher-courses-page__focus-grid">
      <article class="teacher-courses-page__focus-card teacher-courses-page__focus-card--primary">
        <span class="teacher-courses-page__focus-label">当前最重要的事</span>
        <strong>{{ primaryCourse ? `继续建设 ${primaryCourse.title}` : "先激活一门课程" }}</strong>
        <p>{{ primaryCourse ? "先补图谱、资源和题目，再进入阶段评价。" : "没有激活课程时，图谱、评价和学生分析都无法形成闭环。" }}</p>
        <div class="teacher-courses-page__focus-actions">
          <el-button v-if="primaryCourse" type="primary" round @click="openCourseWorkspace(primaryCourse)">进入知识图谱</el-button>
          <el-button v-if="primaryCourse" round @click="openCourseStages(primaryCourse)">阶段评价</el-button>
        </div>
      </article>
      <article class="teacher-courses-page__focus-card">
        <span class="teacher-courses-page__focus-label">页面说明</span>
        <strong>这里负责选课程，不负责做全部事情</strong>
        <p>课程激活后，从这里进入知识图谱工作区、阶段评价页面和其他二级页面，不再把功能堆在首页。</p>
      </article>
    </section>

    <section class="teacher-courses-page__columns">
      <section class="teacher-courses-page__panel">
        <header class="teacher-courses-page__panel-head">
          <h2>已激活课程</h2>
          <el-tag round type="success">{{ myCourses.length }}</el-tag>
        </header>
        <div v-if="myCourses.length" class="teacher-courses-page__card-grid">
          <article v-for="row in myCourses" :key="`mine-${row.id}`" class="teacher-course-card">
            <div class="teacher-course-card__top">
              <span class="teacher-course-card__code">{{ row.code }}</span>
              <h3>{{ row.title }}</h3>
            </div>
            <p>{{ row.description || "管理员暂未填写课程简介。" }}</p>
            <div class="teacher-course-card__chips">
              <span class="teacher-course-card__chip">{{ lifecycleLabel(row.lifecycle_status) }}</span>
              <span class="teacher-course-card__chip teacher-course-card__chip--muted">{{ row.target_class || "班级未绑定" }}</span>
            </div>
            <div class="teacher-course-card__actions">
              <el-button type="primary" round @click="openCourseWorkspace(row)">知识图谱</el-button>
              <el-button round @click="openCourseStages(row)">阶段评价</el-button>
            </div>
          </article>
        </div>
        <el-empty v-else description="暂无已激活课程" />
      </section>

      <section class="teacher-courses-page__panel">
        <header class="teacher-courses-page__panel-head">
          <h2>待激活课程</h2>
          <el-tag round>{{ availableRows.length }}</el-tag>
        </header>
        <div v-if="availableRows.length" class="teacher-courses-page__card-grid">
          <article v-for="row in availableRows" :key="`available-${row.id}`" class="teacher-course-card teacher-course-card--pending">
            <div class="teacher-course-card__top">
              <span class="teacher-course-card__code">{{ row.code }}</span>
              <h3>{{ row.title }}</h3>
            </div>
            <p>{{ row.description || "管理员暂未填写课程简介。" }}</p>
            <div class="teacher-course-card__chips">
              <span class="teacher-course-card__chip" :class="row.can_activate ? 'teacher-course-card__chip--ok' : 'teacher-course-card__chip--warn'">
                {{ row.can_activate ? "可激活" : "待管理员配置" }}
              </span>
            </div>
            <div class="teacher-course-card__actions">
              <el-button type="primary" plain round :disabled="!row.can_activate" :loading="activatingId === row.id" @click="activateCourse(row)">
                激活课程
              </el-button>
            </div>
          </article>
        </div>
        <el-empty v-else description="当前没有待激活课程" />
      </section>
    </section>
  </div>
</template>

<style scoped>
.teacher-courses-page {
  display: grid;
  gap: 18px;
}

.teacher-courses-page__hero,
.teacher-courses-page__panel,
.teacher-courses-page__focus-card,
.teacher-courses-page__stat-card {
  border-radius: 24px;
  border: 1px solid #e3ebf5;
  background: #fff;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}

.teacher-courses-page__hero {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 26px 28px;
  background: linear-gradient(135deg, #eef4ff 0%, #f6fbff 48%, #ffffff 100%);
}

.teacher-courses-page__hero-copy {
  display: grid;
  gap: 8px;
  max-width: 60ch;
}

.teacher-courses-page__eyebrow,
.teacher-courses-page__focus-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-primary-deep);
}

.teacher-courses-page__hero-copy h1,
.teacher-courses-page__focus-card strong {
  margin: 0;
  font-size: 28px;
  color: var(--app-text-main);
}

.teacher-courses-page__hero-copy p,
.teacher-courses-page__focus-card p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--app-text-soft);
}

.teacher-courses-page__hero-actions,
.teacher-courses-page__focus-actions,
.teacher-course-card__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.teacher-courses-page__stats,
.teacher-courses-page__focus-grid,
.teacher-courses-page__columns {
  display: grid;
  gap: 16px;
}

.teacher-courses-page__stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.teacher-courses-page__focus-grid {
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
}

.teacher-courses-page__columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.teacher-courses-page__stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
}

.teacher-courses-page__stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
}

.teacher-courses-page__stat-icon--on { background: linear-gradient(145deg, #3b82f6 0%, #10b981 100%); }
.teacher-courses-page__stat-icon--pending { background: linear-gradient(145deg, #6366f1 0%, #4f8cff 100%); }
.teacher-courses-page__stat-icon--hold { background: linear-gradient(145deg, #94a3b8 0%, #cbd5e1 100%); }

.teacher-courses-page__stat-card span {
  display: block;
  font-size: 12px;
  color: var(--app-text-soft);
}

.teacher-courses-page__stat-card strong {
  font-size: 26px;
  color: var(--app-text-main);
}

.teacher-courses-page__focus-card {
  display: grid;
  gap: 10px;
  padding: 20px 22px;
}

.teacher-courses-page__focus-card--primary {
  background: linear-gradient(145deg, #fdfefe 0%, #eef6ff 100%);
}

.teacher-courses-page__panel {
  overflow: hidden;
}

.teacher-courses-page__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid #edf2f7;
}

.teacher-courses-page__panel-head h2 {
  margin: 0;
  font-size: 18px;
  color: var(--app-text-main);
}

.teacher-courses-page__card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 18px 20px 20px;
}

.teacher-course-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #e6edf5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.teacher-course-card__top {
  display: grid;
  gap: 8px;
}

.teacher-course-card__code {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: var(--app-primary-soft);
  color: var(--app-primary-deep);
}

.teacher-course-card h3 {
  margin: 0;
  font-size: 18px;
  color: var(--app-text-main);
}

.teacher-course-card p {
  margin: 0;
  color: var(--app-text-soft);
  line-height: 1.7;
}

.teacher-course-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.teacher-course-card__chip {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.teacher-course-card__chip--muted { color: #64748b; }
.teacher-course-card__chip--ok { background: rgba(16, 185, 129, 0.1); color: #047857; border-color: rgba(16, 185, 129, 0.28); }
.teacher-course-card__chip--warn { background: rgba(245, 158, 11, 0.12); color: #b45309; border-color: rgba(245, 158, 11, 0.35); }

@media (max-width: 1100px) {
  .teacher-courses-page__stats,
  .teacher-courses-page__focus-grid,
  .teacher-courses-page__columns,
  .teacher-courses-page__card-grid {
    grid-template-columns: 1fr;
  }

  .teacher-courses-page__hero {
    flex-direction: column;
  }
}
</style>
