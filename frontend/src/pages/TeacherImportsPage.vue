<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import TeacherStageImport from "../components/TeacherStageImport.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
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
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/evaluation", query: { ...buildTeacherSubjectQuery(subject.value), tab: "imports" } });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

onMounted(loadCourses);
</script>

<template>
  <div class="teacher-page">
    <WorkspaceTopbar v-model="subject" :courses="courses" badge="教师导入" title="阶段数据导入" @change="syncQuery" />

    <section class="teacher-page__hero">
      <div class="teacher-page__hero-copy">
        <span class="teacher-page__eyebrow">阶段导入工作台</span>
        <h2>把阶段导入做成真正顺手的工作台，而不是信息堆叠页</h2>
        <p>这个页面只做一件事：让老师快速完成导入、复核和追踪，不再出现布局失衡、信息过杂和操作路径过长的问题。</p>
      </div>
    </section>

    <PageSectionCard eyebrow="阶段导入" title="全班阶段数据导入">
      <TeacherStageImport
        :course-id="selectedCourseId"
        :subject="subject"
        :grade="grade"
        @view-profiles="router.push({ path: '/teacher/students', query: { subject: subject || undefined, tab: 'rules' } })"
      />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 20px;
}

.teacher-page__hero {
  padding: 22px 24px;
  border-radius: 24px;
  border: 1px solid #dfe7f2;
  background: linear-gradient(135deg, #ffffff 0%, #eef5ff 100%);
  box-shadow: 0 20px 44px rgba(30, 52, 86, 0.06);
}

.teacher-page__hero-copy {
  display: grid;
  gap: 8px;
}

.teacher-page__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #4a73b8;
}

.teacher-page__hero h2 {
  margin: 0;
  font-size: 26px;
  color: #20344f;
}

.teacher-page__hero p {
  margin: 0;
  max-width: 820px;
  color: #61758f;
  line-height: 1.75;
}
</style>
