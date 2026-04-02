<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import AdminAnalyticsOverview from "../components/AdminAnalyticsOverview.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import HintButton from "../components/HintButton.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };
const route = useRoute(); const router = useRouter();
const subject = ref(""); const grade = ref("通用"); const courses = ref<Course[]>([]);
async function loadCourses() { try { const res = await api.get("/graph/courses"); courses.value = res.data ?? []; subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value); } catch (e:any) { ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败"); } }
function syncQuery() {
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/students", query: { ...buildTeacherSubjectQuery(subject.value), tab: "class" } });
}
watch(subject, () => syncQuery());
watch(() => route.query.subject, (value) => { const next = String(value || "").trim(); if (next && next !== subject.value) subject.value = next; });
onMounted(loadCourses);
</script>
<template>
  <div class="edu-page">
    <header class="edu-header">
      <div class="edu-header__left">
        <h1 class="edu-header__title">课程分析</h1>
        <p class="edu-header__desc">查看当前课程下学生的学习进度、画像分布及能力指标。</p>
      </div>
      <div class="edu-header__actions">
        <el-select v-model="subject" placeholder="切换课程" @change="syncQuery" style="width: 200px">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
        </el-select>
        <div class="edu-header__button-row">
          <el-button class="edu-header__btn" @click="router.push({ path: '/teacher/students', query: { subject: subject || undefined, tab: 'detail' } })">学生详情</el-button>
          <el-button class="edu-header__btn edu-header__btn--accent" @click="router.push({ path: '/teacher/evaluation', query: { subject: subject || undefined, tab: 'behavior' } })">行为画像</el-button>
        </div>
      </div>
    </header>

    <section class="edu-panel">
      <AdminAnalyticsOverview 
        :subject="subject" 
        :grade="grade" 
        :show-student-detail-action="true" 
        @view-student="(id:number)=>router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined, tab: 'detail' } })" 
      />
    </section>
  </div>
</template>
<style scoped>
.teacher-page{display:grid;gap:20px}

.edu-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.edu-header__button-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.edu-header__actions :deep(.el-select__wrapper) {
  min-height: 42px;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px #d7e4f5 inset !important;
}

.edu-header__btn {
  min-width: 118px;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  border: 1px solid #d7e4f5;
  background: #ffffff;
  color: #274263;
  font-size: 14px;
  font-weight: 700;
  box-shadow: none;
}

.edu-header__btn:hover,
.edu-header__btn:focus-visible {
  border-color: #9fbef3;
  background: #f8fbff;
  color: #214d8f;
}

.edu-header__btn.edu-header__btn--accent {
  border-color: #b8cdf3;
  color: #2e5ea8;
}
</style>
