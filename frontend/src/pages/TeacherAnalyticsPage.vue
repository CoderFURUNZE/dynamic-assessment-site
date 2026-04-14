<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminAnalyticsOverview from "../components/AdminAnalyticsOverview.vue";
import HintButton from "../components/HintButton.vue";
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
  router.replace({
    path: "/teacher/students",
    query: { ...buildTeacherSubjectQuery(subject.value), tab: "class" },
  });
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
    <section class="analytics-toolbar">
      <div class="analytics-toolbar__main">
        <div class="analytics-title">
          <span class="analytics-title__eyebrow">学生分析</span>
          <h1>班级总览</h1>
          <p>{{ subject || "未选择课程" }} · {{ grade }}</p>
        </div>
        <div class="analytics-toolbar__course">
          <span>当前课程</span>
          <el-select v-model="subject" placeholder="请选择课程" size="large" style="width: 240px">
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
          </el-select>
        </div>
      </div>
      <div class="analytics-toolbar__actions">
        <HintButton size="small" tip="刷新当前班级分析数据" @click="loadCourses">刷新</HintButton>
        <HintButton
          size="small"
          tip="切换到学生详情视图"
          @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'detail' } })"
        >
          切换视图
        </HintButton>
      </div>
    </section>

    <section class="edu-panel">
      <AdminAnalyticsOverview
        :subject="subject"
        :grade="grade"
        :show-student-detail-action="true"
        @view-student="(id:number) => router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined, tab: 'detail' } })"
      />
    </section>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 24px;
}

.analytics-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 24px 22px;
  border: 1px solid #dbe7f6;
  border-radius: 20px;
  background: linear-gradient(180deg, #dfeafb 0%, #edf4ff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.analytics-toolbar__main,
.analytics-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.analytics-toolbar__course {
  display: grid;
  gap: 6px;
  padding: 0 0 0 4px;
}

.analytics-toolbar__course span {
  font-size: 12px;
  font-weight: 600;
  color: #355b93;
}

.analytics-title {
  display: grid;
  gap: 4px;
}

.analytics-title__eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5b83d6;
}

.analytics-title h1 {
  margin: 0;
  font-size: 20px;
  line-height: 1.1;
  font-weight: 800;
  color: #0f172a;
}

.analytics-title p {
  margin: 0;
  font-size: 12px;
  color: #557198;
}

:deep(.analytics-toolbar .el-select__wrapper) {
  min-height: 40px;
  border-radius: 12px;
  box-shadow: none;
  background: rgba(255, 255, 255, 0.88);
}

:deep(.analytics-toolbar .el-select__placeholder),
:deep(.analytics-toolbar .el-select__selected-item) {
  color: #355b93;
}

@media (max-width: 768px) {
  .analytics-toolbar {
    align-items: stretch;
    padding: 20px 18px;
  }

  .analytics-toolbar__course {
    width: 100%;
    padding-left: 0;
  }
}
</style>
