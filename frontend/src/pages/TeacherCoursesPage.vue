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
  <div class="teacher-course-page" v-loading="loading">
    <section class="teacher-course-header">
      <div class="teacher-course-header__main">
        <h1 class="teacher-course-header__title">课程</h1>
      </div>
      <div class="teacher-course-header__actions">
        <el-button type="primary" @click="loadCatalog" :loading="loading">刷新课程列表</el-button>
      </div>
    </section>

    <section class="teacher-course-summary">
      <div class="teacher-course-summary__item">
        <span>我已激活</span>
        <strong>{{ myCourses.length }}</strong>
      </div>
      <div class="teacher-course-summary__item">
        <span>可激活</span>
        <strong>{{ availableRows.filter((item) => item.can_activate).length }}</strong>
      </div>
      <div class="teacher-course-summary__item">
        <span>暂不可用</span>
        <strong>{{ disabledRows.length }}</strong>
      </div>
    </section>

    <section class="teacher-course-board">
      <div class="teacher-course-panel">
        <div class="teacher-course-column__head">
          <div>
            <div class="teacher-course-column__title">我已激活的课程</div>
          </div>
          <span class="teacher-course-column__badge">{{ myCourses.length }} 门</span>
        </div>

        <div v-if="myCourses.length" class="teacher-course-list">
          <article v-for="row in myCourses" :key="`mine-${row.id}`" class="teacher-course-card teacher-course-card--active">
            <div class="teacher-course-card__head">
              <div class="teacher-course-card__main">
                <div class="teacher-course-card__code">{{ row.code }}</div>
                <div>
                  <div class="teacher-course-card__title">{{ row.title }}</div>
                  <div class="teacher-course-card__desc">{{ row.description || "管理员暂未填写课程简介。" }}</div>
                </div>
              </div>
              <el-tag size="small" type="success">已激活</el-tag>
            </div>
            <div class="teacher-course-card__info">
              <span>教学状态：{{ lifecycleLabel(row.lifecycle_status) }}</span>
              <span>目标班级：{{ row.target_class || "未绑定班级" }}</span>
              <span>开课时间：{{ row.start_at ? row.start_at.replace("T", " ").slice(0, 16) : "未设置" }}</span>
              <span>报名状态：{{ enrollStatusLabel(row.enroll_status) }}</span>
              <span>人数上限：{{ row.max_students ?? 200 }}</span>
            </div>
            <div class="teacher-course-card__actions">
              <el-button type="primary" @click="openCourseWorkspace(row)">进入图谱工作区</el-button>
              <el-button @click="openCourseStages(row)">进入阶段管理</el-button>
            </div>
          </article>
        </div>
        <div v-else class="teacher-course-empty">
          <div class="teacher-course-empty__title">暂无已激活课程</div>
        </div>
      </div>

      <div class="teacher-course-panel">
        <div class="teacher-course-column__head">
          <div>
            <div class="teacher-course-column__title">可激活课程</div>
          </div>
          <span class="teacher-course-column__badge">{{ availableRows.length }} 门</span>
        </div>

        <div v-if="availableRows.length" class="teacher-course-list">
          <article v-for="row in availableRows" :key="`available-${row.id}`" class="teacher-course-card">
            <div class="teacher-course-card__head">
              <div class="teacher-course-card__main">
                <div class="teacher-course-card__code">{{ row.code }}</div>
                <div>
                  <div class="teacher-course-card__title">{{ row.title }}</div>
                  <div class="teacher-course-card__desc">{{ row.description || "管理员暂未填写课程简介。" }}</div>
                </div>
              </div>
              <el-tag size="small" :type="row.can_activate ? 'info' : 'warning'">{{ courseStatusText(row) }}</el-tag>
            </div>
            <div class="teacher-course-card__info">
              <span>课程状态：{{ row.active ? "已启用" : "未启用" }}</span>
              <span>教学状态：{{ lifecycleLabel(row.lifecycle_status) }}</span>
              <span>目标班级：{{ row.target_class || "未绑定班级" }}</span>
              <span>报名状态：{{ enrollStatusLabel(row.enroll_status) }}</span>
            </div>
            <div class="teacher-course-card__info" v-if="row.start_at || row.end_at || row.activation_status">
              <span>开课时间：{{ row.start_at ? row.start_at.replace("T", " ").slice(0, 16) : "未设置" }}</span>
              <span>结束时间：{{ row.end_at ? row.end_at.replace("T", " ").slice(0, 16) : "未设置" }}</span>
              <span>{{ row.activation_status || "管理员配置后可激活" }}</span>
            </div>
            <div class="teacher-course-card__actions">
              <el-button
                type="primary"
                :disabled="!row.can_activate"
                :loading="activatingId === row.id"
                @click="activateCourse(row)"
              >
                激活这门课
              </el-button>
            </div>
          </article>
        </div>
        <div v-else class="teacher-course-empty">
          <div class="teacher-course-empty__title">暂无可激活课程</div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.teacher-course-page {
  display: grid;
  gap: 16px;
}

.teacher-course-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 18px 20px;
  border-radius: 22px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.teacher-course-header__main {
  display: grid;
  gap: 8px;
}

.teacher-course-header__title {
  margin: 0;
  font-size: 24px;
  line-height: 1.2;
  font-weight: 800;
  color: #1d3250;
}

.teacher-course-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.teacher-course-summary__item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
  display: grid;
  gap: 6px;
}

.teacher-course-summary__item span {
  color: #6c8099;
  font-size: 13px;
}

.teacher-course-summary__item strong {
  color: #213858;
  font-size: 28px;
}

.teacher-course-board {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}

.teacher-course-panel {
  padding: 18px;
  border-radius: 22px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
  display: grid;
  gap: 14px;
  align-content: start;
}

.teacher-course-column__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.teacher-course-column__title {
  font-size: 20px;
  font-weight: 800;
  color: #1f3655;
}

.teacher-course-column__desc {
  display: none;
}

.teacher-course-column__badge {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  background: #eef4ff;
  color: #2c5aa1;
  font-size: 13px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.teacher-course-list {
  display: grid;
  gap: 12px;
}

.teacher-course-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #dce5f0;
  background: #ffffff;
  box-shadow: none;
  display: grid;
  gap: 10px;
}

.teacher-course-card--active {
  background: linear-gradient(180deg, #ffffff 0%, #f4f8ff 100%);
}

.teacher-course-card__head,
.teacher-course-card__info,
.teacher-course-card__actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.teacher-course-card__main {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.teacher-course-card__code {
  width: fit-content;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #eef4ff;
  color: #2b5aa1;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.teacher-course-card__title {
  font-size: 20px;
  font-weight: 800;
  color: #203756;
}

.teacher-course-card__desc {
  color: #566b85;
  line-height: 1.65;
  font-size: 14px;
}

.teacher-course-card__info {
  color: #6d8098;
  font-size: 13px;
}

.teacher-course-empty {
  min-height: 220px;
  border-radius: 18px;
  border: 1px dashed #d7e1ec;
  background: #fbfcfe;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 24px;
}

.teacher-course-empty__title {
  font-size: 18px;
  font-weight: 800;
  color: #233b5b;
}

.teacher-course-empty__text {
  display: none;
}

@media (max-width: 1100px) {
  .teacher-course-summary,
  .teacher-course-board {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .teacher-course-header {
    flex-direction: column;
    padding: 16px;
  }

  .teacher-course-header__title {
    font-size: 24px;
  }

  .teacher-course-panel {
    padding: 16px;
  }
}
</style>
