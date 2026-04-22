<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherStageImport from "../components/TeacherStageImport.vue";
import TeacherWorkspaceHero from "../components/TeacherWorkspaceHero.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();

const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);

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
  const nextQuery = { ...buildTeacherSubjectQuery(subject.value), tab: "imports" };
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "stages").trim();
  if (
    route.path === "/teacher/evaluation"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "imports"
  ) {
    return;
  }
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/evaluation", query: nextQuery });
}

function goResults() {
  router.push({ path: "/teacher/evaluation", query: { ...buildTeacherSubjectQuery(subject.value), tab: "behavior" } });
}

function goHistory() {
  router.push({
    path: "/teacher/evaluation",
    query: { ...buildTeacherSubjectQuery(subject.value), tab: "imports", section: "history" },
  });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = resolveTeacherSubject(String(value || ""), subject.value, courses.value);
    if (next && next !== subject.value) subject.value = next;
  },
);

onMounted(loadCourses);
</script>

<template>
  <div class="imports-page">
    <TeacherWorkspaceHero
      v-model="subject"
      title="数据导入"
      pill="数据流转"
      description="按课程和阶段导入汇总数据、整理文件或行为信号，再进入结果页查看最新画像。"
      field-label="当前课程"
      :courses="courses"
    >
      <template #meta>
        <span class="imports-page__meta-pill">{{ subject || "未选择课程" }}</span>
        <span class="imports-page__meta-pill imports-page__meta-pill--muted">{{ grade }}</span>
      </template>
      <template #actions>
        <button class="imports-page__btn" type="button" @click="goHistory">导入历史</button>
        <button class="imports-page__btn imports-page__btn--primary" type="button" @click="goResults">查看结果</button>
      </template>
    </TeacherWorkspaceHero>

    <section class="imports-page__panel">
      <TeacherStageImport
        :course-id="selectedCourseId"
        :subject="subject"
        :grade="grade"
        @view-profiles="goResults"
      />
    </section>
  </div>
</template>

<style scoped>
.imports-page {
  display: grid;
  gap: 24px;
}

.imports-page__meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  background: rgba(255, 255, 255, 0.82);
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.imports-page__meta-pill--muted {
  color: #64748b;
}

.imports-page__btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: #ffffff;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.imports-page__btn--primary {
  background: #16a34a;
  border-color: rgba(34, 197, 94, 0.3);
  color: #fff;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
}

.imports-page__btn:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.28);
}

.imports-page__btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.14);
}

.imports-page__panel {
  min-width: 0;
  padding: 20px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: #ffffff;
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

@media (prefers-reduced-motion: reduce) {
  .imports-page__btn {
    transition: none;
  }
}
</style>
