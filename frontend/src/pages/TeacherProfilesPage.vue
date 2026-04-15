<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

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
  router.replace({ path: "/teacher/students", query: { ...buildTeacherSubjectQuery(subject.value), tab: "results" } });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  },
);

onMounted(loadCourses);
</script>

<template>
  <div class="teacher-page">
    <section class="profiles-hero">
      <div class="profiles-hero__eyebrow">结果查看</div>
      <div class="profiles-hero__headline">
        <h1 class="profiles-hero__title">画像结果</h1>
        <span class="profiles-hero__pill">结果查看</span>
      </div>
    </section>

    <section class="teacher-profiles-panel">
      <AdminPersonaManager
        :subject="subject"
        :grade="grade"
        :readonly="true"
        step="results"
        :show-student-detail-action="true"
        @view-student="(id:number)=>router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined, tab: 'detail' } })"
      />
    </section>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 20px;
}

.profiles-hero {
  padding: 26px 24px;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.profiles-hero__eyebrow {
  font-size: 12px;
  font-weight: 700;
  color: #5d8666;
}

.profiles-hero__headline {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.profiles-hero__title {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  font-weight: 800;
  color: #1f5130;
}

.profiles-hero__pill {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: #eef5ff;
  color: #355070;
  font-size: 13px;
  font-weight: 700;
}

.teacher-profiles-panel {
  min-width: 0;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  padding: 24px;
}

@media (max-width: 760px) {
  .profiles-hero {
    padding: 22px 18px;
  }

  .profiles-hero__title {
    font-size: 18px;
  }

  .teacher-profiles-panel {
    padding: 18px;
  }
}
</style>
