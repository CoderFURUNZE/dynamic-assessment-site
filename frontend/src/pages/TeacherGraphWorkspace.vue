<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
};

type WorkbenchState = {
  kpCount: number;
  categoryCount: number;
  filteredCount: number;
  selectedType: "kp" | "category";
  selectedKpId: number | null;
  selectedCategory: string | null;
};

const route = useRoute();
const router = useRouter();

const isTeacher = computed(() => getRole() === "teacher");
const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const workbenchState = ref<WorkbenchState>({
  kpCount: 0,
  categoryCount: 0,
  filteredCount: 0,
  selectedType: "kp",
  selectedKpId: null,
  selectedCategory: null,
});

const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const isReadonlyCourse = computed(() => {
  const course = currentCourse.value;
  if (!course) return false;
  if (String(course.lifecycle_status || "").toLowerCase() === "archived") return true;
  if (course.end_at) {
    const end = new Date(course.end_at).getTime();
    if (Number.isFinite(end) && end < Date.now()) return true;
  }
  return false;
});

const summaryCards = computed(() => [
  { label: "知识点", value: String(workbenchState.value.kpCount) },
  { label: "分类", value: String(workbenchState.value.categoryCount) },
  {
    label: "当前选中",
    value:
      workbenchState.value.selectedType === "category" && workbenchState.value.selectedCategory
        ? workbenchState.value.selectedCategory
        : workbenchState.value.selectedKpId
          ? `#${workbenchState.value.selectedKpId}`
          : "未选择",
  },
  { label: "状态", value: isReadonlyCourse.value ? "只读" : "可编辑" },
]);

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  router.replace({
    path: "/teacher/content",
    query: buildTeacherSubjectQuery(subject.value),
  });
}

function updateWorkbenchState(payload: WorkbenchState) {
  workbenchState.value = payload;
}

async function refreshWorkspace() {
  await loadCourses();
}

function goBack() {
  router.push({ path: "/teacher/workspace", query: buildTeacherSubjectQuery(subject.value) });
}

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "");
    if (next && next !== subject.value) subject.value = next;
  },
);

watch(subject, () => {
  syncQuery();
});

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问知识图谱");
    router.push("/login/student");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="graph-page">
    <section class="graph-page__hero">
      <div class="graph-page__hero-copy">
        <span class="graph-page__eyebrow">课程工作台</span>
        <h1>知识图谱建设</h1>
        <p>{{ currentCourse?.title || "当前课程" }}</p>
      </div>
      <div class="graph-page__hero-actions">
        <el-select v-model="subject" class="graph-page__select" placeholder="选择课程">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <el-button @click="goBack">返回工作台</el-button>
        <el-button type="primary" @click="refreshWorkspace">刷新</el-button>
      </div>
    </section>

    <section class="graph-page__stats">
      <article v-for="item in summaryCards" :key="item.label" class="graph-page__stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="graph-page__panel">
      <header class="graph-page__panel-head">
        <div>
          <h2>知识图谱建设</h2>
          <span>{{ currentCourse?.code || "课程图谱" }}</span>
        </div>
      </header>

      <div class="graph-page__panel-body">
        <TeacherGraphWorkbench
          :subject="subject"
          :grade="grade"
          :fullscreen="true"
          :embedded="true"
          :readonly="isReadonlyCourse"
          @state-change="updateWorkbenchState"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px 24px;
  display: grid;
  gap: 18px;
}

.graph-page__hero,
.graph-page__panel,
.graph-page__stat-card {
  border-radius: 24px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 14%, var(--app-border));
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.graph-page__hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 22px 24px;
  background:
    radial-gradient(circle at top right, rgba(79, 140, 255, 0.12), transparent 30%),
    linear-gradient(135deg, #eef4ff 0%, #f6fbff 52%, #ffffff 100%);
}

.graph-page__hero-copy {
  display: grid;
  gap: 8px;
  max-width: 760px;
}

.graph-page__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5a7db7;
}

.graph-page__hero-copy h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.18;
  color: #11284a;
  letter-spacing: -0.03em;
}

.graph-page__hero-copy p {
  margin: 0;
  color: #60758f;
  font-size: 14px;
  line-height: 1.6;
}

.graph-page__hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.graph-page__select {
  width: 240px;
}

.graph-page__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.graph-page__stat-card {
  padding: 18px 20px;
  display: grid;
  gap: 8px;
  min-height: 96px;
}

.graph-page__stat-card span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.graph-page__stat-card strong {
  font-size: 28px;
  color: var(--app-text-main);
  line-height: 1;
}

.graph-page__panel {
  padding: 18px 18px 10px;
}

.graph-page__panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.graph-page__panel-head h2 {
  margin: 0;
  font-size: 20px;
  color: var(--app-text-main);
}

.graph-page__panel-head span {
  color: var(--app-text-soft);
  font-size: 13px;
}

.graph-page__panel-body {
  overflow: hidden;
  min-height: min(82vh, 960px);
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
  border-radius: 20px;
  padding: 8px;
}

@media (max-width: 1100px) {
  .graph-page__hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .graph-page__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .graph-page {
    padding: 0 16px 20px;
  }

  .graph-page__hero-copy h1 {
    font-size: 24px;
  }

  .graph-page__select {
    width: 100%;
  }

  .graph-page__stats {
    grid-template-columns: 1fr;
  }

  .graph-page__panel-body {
    min-height: min(72vh, 840px);
  }
}
</style>
