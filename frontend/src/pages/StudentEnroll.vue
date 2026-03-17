<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

type EnrollableCourse = {
  id: number;
  code: string;
  title: string;
  description: string;
  teacher_name?: string;
  max_students: number;
  enrolled_count: number;
  apply_deadline?: string | null;
  enroll_status: string;
  application_status?: string | null;
};

type CourseApplication = {
  id: number;
  course_title: string;
  status: string;
  apply_reason: string;
  review_remark: string;
  reject_reason: string;
  created_at: string;
  reviewed_at?: string | null;
};

type Notice = {
  id: number;
  title: string;
  content: string;
  status: string;
  created_at: string;
};

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const applying = ref<number | null>(null);
const courses = ref<EnrollableCourse[]>([]);
const applications = ref<CourseApplication[]>([]);
const notices = ref<Notice[]>([]);
const applyReasonMap = ref<Record<number, string>>({});

function normalizeStatus(status?: string | null) {
  return String(status || "").trim().toLowerCase();
}

function statusLabel(status: string) {
  const value = normalizeStatus(status);
  if (value === "open") return "可报名";
  if (value === "full") return "已满";
  if (value === "closed") return "已关闭";
  if (value === "expired") return "已过期";
  return status;
}

function appStatusLabel(status?: string | null) {
  const value = normalizeStatus(status);
  if (!value) return "未报名";
  if (value === "pending") return "审核中";
  if (value === "approved") return "已通过";
  if (value === "rejected") return "已拒绝";
  return status;
}

async function loadAll() {
  loading.value = true;
  try {
    const [courseRes, appRes, noticeRes] = await Promise.all([
      api.get("/enrollment/courses/enrollable"),
      api.get("/enrollment/my/applications"),
      api.get("/enrollment/my/notifications"),
    ]);
    courses.value = courseRes.data?.items ?? [];
    applications.value = appRes.data?.items ?? [];
    notices.value = noticeRes.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载报名数据失败");
  } finally {
    loading.value = false;
  }
}

async function applyCourse(course: EnrollableCourse) {
  if (course.application_status) {
    ElMessage.warning(`当前状态：${appStatusLabel(course.application_status)}`);
    return;
  }
  applying.value = course.id;
  try {
    await api.post(`/enrollment/courses/${course.id}/apply`, {
      apply_reason: applyReasonMap.value[course.id] || "",
    });
    ElMessage.success("报名已提交，等待老师审核");
    await loadAll();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "报名失败");
  } finally {
    applying.value = null;
  }
}

async function markRead(noticeId: number) {
  try {
    await api.post(`/enrollment/my/notifications/${noticeId}/read`);
    notices.value = notices.value.map((item) => (item.id === noticeId ? { ...item, status: "READ" } : item));
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新通知失败");
  }
}

function goBackStudy() {
  const preview = String(route.query.preview || "");
  router.push({
    path: "/student/overview",
    query: preview ? { preview } : undefined,
  });
}

onMounted(loadAll);
</script>

<template>
  <div class="enroll-page" v-loading="loading">
    <header class="enroll-header panel-card">
      <div>
        <div class="enroll-kicker">Course Enrollment</div>
        <h1>课程报名与审核状态</h1>
      </div>
      <div class="enroll-header__actions">
        <el-button @click="goBackStudy">返回学习中心</el-button>
        <el-button type="primary" @click="loadAll">刷新</el-button>
      </div>
    </header>

    <section class="panel-card block">
      <div class="block__head">
        <h3>可报名课程</h3>
      </div>
      <div class="enroll-list">
        <div v-for="course in courses" :key="course.id" class="enroll-item">
          <div class="enroll-item__main">
            <strong>{{ course.title }}</strong>
            <span>{{ course.code }} · {{ course.teacher_name || "未分配老师" }}</span>
            <span>名额 {{ course.enrolled_count }}/{{ course.max_students }} · {{ statusLabel(course.enroll_status) }}</span>
            <span v-if="course.apply_deadline">截止：{{ course.apply_deadline.replace("T", " ").slice(0, 16) }}</span>
            <span>当前报名状态：{{ appStatusLabel(course.application_status) }}</span>
          </div>
          <div class="enroll-item__actions">
            <el-input
              v-model="applyReasonMap[course.id]"
              placeholder="可填写报名理由（选填）"
              style="width: 260px"
              :disabled="!!course.application_status"
            />
            <el-button
              type="primary"
              :loading="applying === course.id"
              :disabled="!!course.application_status || normalizeStatus(course.enroll_status) !== 'open'"
              @click="applyCourse(course)"
            >
              提交报名
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel-card block">
      <div class="block__head">
        <h3>我的报名记录</h3>
      </div>
      <el-table :data="applications" size="small">
        <el-table-column prop="course_title" label="课程" min-width="180" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="apply_reason" label="报名理由" min-width="180" />
        <el-table-column prop="review_remark" label="审核备注" min-width="160" />
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="180" />
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 16) }}</template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel-card block">
      <div class="block__head">
        <h3>站内通知</h3>
      </div>
      <div v-if="notices.length === 0" class="empty">暂无通知</div>
      <div v-else class="notice-list">
        <div v-for="notice in notices" :key="notice.id" class="notice-item">
          <div>
            <strong>{{ notice.title }}</strong>
            <p>{{ notice.content }}</p>
            <small>{{ notice.created_at.replace("T", " ").slice(0, 16) }}</small>
          </div>
          <el-button size="small" :disabled="normalizeStatus(notice.status) === 'read'" @click="markRead(notice.id)">
            {{ normalizeStatus(notice.status) === "read" ? "已读" : "标记已读" }}
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.enroll-page { display: grid; gap: 18px; padding: 18px; }
.panel-card {
  background: #ffffff;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  padding: 20px;
  box-shadow: var(--app-shadow-soft);
}
.enroll-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
}
.enroll-kicker { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: #6d87ab; font-weight: 800; }
.enroll-header h1 { margin: 8px 0; font-size: 30px; line-height: 1.15; color: #24374f; }
.enroll-header__actions { display: flex; gap: 8px; flex-wrap: wrap; }
.block { display: grid; gap: 14px; }
.block__head h3 { margin: 0; color: #24374f; font-size: 18px; }
.enroll-list, .notice-list { display: grid; gap: 12px; }
.enroll-item, .notice-item {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  background: #fcfdff;
}
.enroll-item__main { display: grid; gap: 6px; }
.enroll-item__main strong { color: #253d58; font-size: 16px; }
.enroll-item__main span, .notice-item p, .notice-item small { color: #6f829b; margin: 0; line-height: 1.6; }
.enroll-item__actions { display: flex; gap: 8px; align-items: center; }
.empty { color: #7c8da2; padding: 4px 0; }
@media (max-width: 980px) {
  .enroll-header, .enroll-item, .notice-item { flex-direction: column; align-items: flex-start; }
  .enroll-item__actions { width: 100%; flex-direction: column; align-items: stretch; }
}
</style>
