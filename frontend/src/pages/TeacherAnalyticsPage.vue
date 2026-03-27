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
function syncQuery() { saveTeacherSubject(subject.value); router.replace({ path: "/teacher/analytics", query: buildTeacherSubjectQuery(subject.value) }); }
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
        <el-button-group style="margin-left: 12px">
          <el-button @click="router.push({ path: '/teacher/students', query: { subject: subject || undefined } })">学生详情</el-button>
          <el-button type="primary" @click="router.push({ path: '/teacher/behavior-report', query: { subject: subject || undefined } })">行为画像</el-button>
        </el-button-group>
      </div>
    </header>

    <section class="edu-panel">
      <AdminAnalyticsOverview 
        :subject="subject" 
        :grade="grade" 
        :show-student-detail-action="true" 
        @view-student="(id:number)=>router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined } })" 
      />
    </section>
  </div>
</template>
<style scoped>.teacher-page{display:grid;gap:20px}</style>
