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
  enrollment_mode?: string;
  target_class?: string | null;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
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
const activeTab = ref<"search" | "applications" | "notifications">("search");
const keyword = ref("");

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
  if (value === "linked") return "已自动关联";
  if (value === "rejected") return "已拒绝";
  return status || "--";
}

function autoJoinHint(course: EnrollableCourse) {
  if (normalizeStatus(course.application_status) === "linked") return "系统已自动关联，可直接进入学习。";
  if (normalizeStatus(course.application_status) === "approved") return "你已加入这门课程。";
  if (normalizeStatus(course.application_status) === "pending") return "申请已提交，等待老师审核。";
  if (normalizeStatus(course.lifecycle_status) === "archived") return "课程已归档，仅保留查看记录。";
  if (normalizeStatus(course.lifecycle_status) === "draft") return "课程未正式开课，开课后可加入。";
  if (normalizeStatus(course.enrollment_mode) === "class_auto") return `系统会按班级 ${course.target_class || ""} 自动关联。`;
  if (normalizeStatus(course.enroll_status) !== "open") return "当前不在开放报名时间。";
  return "搜索课程后，可直接查看状态并提交申请。";
}

const filteredCourses = computed(() => {
  const q = keyword.value.trim().toLowerCase();
  if (!q) return courses.value;
  return courses.value.filter((course) => [course.title, course.code, course.teacher_name || ""].join(" ").toLowerCase().includes(q));
});

const stats = computed(() => ({
  available: courses.value.filter((course) => normalizeStatus(course.enroll_status) === "open").length,
  pending: applications.value.filter((item) => normalizeStatus(item.status) === "pending").length,
  unread: notices.value.filter((item) => normalizeStatus(item.status) !== "read").length,
}));

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
    ElMessage.success("申请已提交，等待老师审核");
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
    path: "/student/dashboard",
    query: preview ? { preview } : undefined,
  });
}

onMounted(loadAll);
</script>

<template>
  <div class="enroll-page" v-loading="loading">
    <section class="enroll-page__hero">
      <div class="enroll-page__hero-copy">
        <span class="enroll-page__eyebrow">课程加入</span>
        <h1>先搜索课程，再看申请记录和站内通知</h1>
        <p>这个页面只处理课程搜索、报名记录和通知，不再堆长篇说明。</p>
      </div>
      <div class="enroll-page__hero-actions">
        <el-button @click="goBackStudy">返回学习中心</el-button>
        <el-button type="primary" @click="loadAll">刷新</el-button>
      </div>
    </section>

    <section class="enroll-page__stats">
      <article class="enroll-page__stat-card"><span>可报名课程</span><strong>{{ stats.available }}</strong></article>
      <article class="enroll-page__stat-card"><span>待审核申请</span><strong>{{ stats.pending }}</strong></article>
      <article class="enroll-page__stat-card"><span>未读通知</span><strong>{{ stats.unread }}</strong></article>
    </section>

    <el-tabs v-model="activeTab" class="enroll-tabs">
      <el-tab-pane name="search" label="课程搜索">
        <section class="enroll-page__toolbar panel-card">
          <div class="enroll-page__toolbar-group enroll-page__toolbar-group--search">
            <span class="enroll-page__field-label">搜索课程</span>
            <el-input v-model="keyword" size="large" placeholder="" clearable class="keyword-input" />
            <span class="enroll-page__toolbar-note">支持课程名、课程代码、教师名检索</span>
          </div>
        </section>

        <section class="enroll-page__list">
          <article v-for="course in filteredCourses" :key="course.id" class="enroll-course-card panel-card">
            <div class="enroll-course-card__main">
              <div class="enroll-course-card__top">
                <div class="enroll-course-card__title-block">
                  <strong>{{ course.title }}</strong>
                  <p>{{ course.code }} · {{ course.teacher_name || '未分配教师' }}</p>
                </div>
                <el-tag round>{{ appStatusLabel(course.application_status) }}</el-tag>
              </div>
              <div class="enroll-course-card__chips">
                <span>{{ statusLabel(course.enroll_status) }}</span>
                <span>名额 {{ course.enrolled_count }}/{{ course.max_students }}</span>
                <span v-if="course.target_class">班级 {{ course.target_class }}</span>
              </div>
              <p class="enroll-course-card__desc">{{ course.description || autoJoinHint(course) }}</p>
              <div class="enroll-course-card__meta">
                <span>{{ autoJoinHint(course) }}</span>
              </div>
            </div>
            <div class="enroll-course-card__actions">
              <div class="enroll-course-card__reason-head">
                <span class="enroll-course-card__reason-label">申请理由（可选）</span>
                <span class="enroll-course-card__reason-tip">可留空，直接提交即可</span>
              </div>
              <div class="enroll-course-card__action-row">
                <el-input
                  v-model="applyReasonMap[course.id]"
                  placeholder=""
                  :disabled="!!course.application_status || normalizeStatus(course.enrollment_mode) === 'class_auto'"
                />
                <el-button
                  type="primary"
                  plain
                  :loading="applying === course.id"
                  :disabled="!!course.application_status || normalizeStatus(course.enroll_status) !== 'open' || normalizeStatus(course.enrollment_mode) === 'class_auto'"
                  @click="applyCourse(course)"
                >
                  {{ normalizeStatus(course.enrollment_mode) === 'class_auto' ? '自动关联课程' : '申请加入' }}
                </el-button>
              </div>
            </div>
          </article>
          <el-empty v-if="filteredCourses.length === 0" description="没有匹配到课程" />
        </section>
      </el-tab-pane>

      <el-tab-pane name="applications" label="报名记录">
        <section class="panel-card enroll-table-card">
          <header class="enroll-table-card__head">
            <h3>我的报名记录</h3>
            <span>共 {{ applications.length }} 条</span>
          </header>
          <el-table :data="applications" size="small">
            <el-table-column prop="course_title" label="课程" min-width="180" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="apply_reason" label="申请理由" min-width="180" />
            <el-table-column prop="review_remark" label="审核备注" min-width="160" />
            <el-table-column prop="reject_reason" label="拒绝原因" min-width="180" />
            <el-table-column prop="created_at" label="提交时间" width="170">
              <template #default="{ row }">{{ row.created_at.replace('T', ' ').slice(0, 16) }}</template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane name="notifications" label="站内通知">
        <section class="panel-card enroll-table-card">
          <header class="enroll-table-card__head">
            <h3>站内通知</h3>
            <span>未读 {{ stats.unread }}</span>
          </header>
          <div v-if="notices.length === 0" class="empty">暂无通知</div>
          <div v-else class="notice-list">
            <div v-for="notice in notices" :key="notice.id" class="notice-item">
              <div>
                <strong>{{ notice.title }}</strong>
                <p>{{ notice.content }}</p>
                <small>{{ notice.created_at.replace('T', ' ').slice(0, 16) }}</small>
              </div>
              <el-button size="small" :disabled="normalizeStatus(notice.status) === 'read'" @click="markRead(notice.id)">
                {{ normalizeStatus(notice.status) === 'read' ? '已读' : '标记已读' }}
              </el-button>
            </div>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.enroll-page {
  display: grid;
  gap: 18px;
  padding-bottom: 12px;
}
.enroll-page__hero,
.enroll-page__toolbar,
.enroll-course-card,
.enroll-page__stat-card,
.enroll-table-card {
  border-radius: 24px;
  border: 1px solid #e3ebf5;
  background: #fff;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}
.enroll-page__hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 22px 24px;
  background:
    radial-gradient(circle at top right, rgba(79, 140, 255, 0.12), transparent 30%),
    linear-gradient(135deg, #eef4ff 0%, #f6fbff 52%, #ffffff 100%);
}
.enroll-page__hero-copy {
  display: grid;
  gap: 8px;
  max-width: 760px;
}
.enroll-page__eyebrow { font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--app-primary-deep); }
.enroll-page__hero h1 { margin: 0; font-size: 28px; color: var(--app-text-main); line-height: 1.18; letter-spacing: -0.03em; }
.enroll-page__hero p { margin: 0; line-height: 1.65; color: var(--app-text-soft); font-size: 14px; }
.enroll-page__hero-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.enroll-page__stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.enroll-page__stat-card { padding: 18px 20px; display: grid; gap: 8px; min-height: 96px; }
.enroll-page__stat-card span { font-size: 12px; color: var(--app-text-soft); }
.enroll-page__stat-card strong { font-size: 28px; color: var(--app-text-main); line-height: 1; }
.enroll-page__toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  padding: 16px;
  margin-bottom: 14px;
  align-items: stretch;
}
.enroll-page__toolbar-group {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid color-mix(in srgb, var(--app-border) 88%, #ffffff);
  background: linear-gradient(180deg, #fbfdff 0%, #f8fbff 100%);
}
.enroll-page__toolbar-group--search { align-content: start; }
.enroll-page__field-label {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: var(--app-text-main);
}
.enroll-page__toolbar-note {
  font-size: 12px;
  color: var(--app-text-soft);
}
.enroll-page__list, .notice-list { display: grid; gap: 12px; }
.enroll-course-card {
  padding: 20px 22px;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(260px, 0.75fr);
  gap: 18px;
  align-items: stretch;
}
.enroll-course-card__top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.enroll-course-card__title-block { display: grid; gap: 4px; }
.enroll-course-card__top strong { font-size: 19px; color: var(--app-text-main); }
.enroll-course-card__top p, .enroll-course-card__desc, .notice-item p, .notice-item small { margin: 0; color: var(--app-text-soft); line-height: 1.6; }
.enroll-course-card__desc { font-size: 14px; }
.enroll-course-card__meta {
  font-size: 12px;
  color: var(--app-text-soft);
  line-height: 1.6;
  padding-top: 2px;
}
.enroll-course-card__chips { display: flex; gap: 8px; flex-wrap: wrap; }
.enroll-course-card__chips span { padding: 5px 10px; border-radius: 999px; border: 1px solid #dbe6f2; background: #f8fbff; font-size: 12px; color: #58718f; }
.enroll-course-card__main {
  display: grid;
  gap: 12px;
  align-content: start;
  padding-right: 4px;
}
.enroll-course-card__actions {
  align-items: stretch;
  padding: 16px;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.98));
  border: 1px solid color-mix(in srgb, var(--app-border) 84%, #ffffff);
  flex-direction: column;
  justify-content: center;
  min-height: 100%;
}
.enroll-course-card__reason-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
}
.enroll-course-card__reason-label { font-size: 12px; font-weight: 800; color: var(--app-text-main); }
.enroll-course-card__reason-tip { font-size: 12px; color: var(--app-text-light); }
.enroll-course-card__action-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}
.keyword-input { width: 100%; }
.enroll-page__toolbar :deep(.el-input__wrapper) {
  border-radius: 16px;
  min-height: 48px;
}
.enroll-page__toolbar :deep(.el-button) {
  border-radius: 16px;
  min-height: 48px;
  padding-inline: 18px;
}
.enroll-course-card__actions :deep(.el-input__wrapper) {
  border-radius: 16px;
  min-height: 46px;
}
.enroll-course-card__actions :deep(.el-button) {
  border-radius: 16px;
  min-height: 46px;
  padding-inline: 18px;
}
.enroll-table-card { padding: 18px 20px; }
.enroll-table-card__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.enroll-table-card__head h3 { margin: 0; font-size: 18px; color: var(--app-text-main); }
.enroll-table-card__head span { color: var(--app-text-soft); font-size: 13px; }
.notice-item {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  background: linear-gradient(180deg, #fcfdff 0%, #f7fbff 100%);
}
.empty { color: #7c8da2; padding: 6px 0; }
@media (max-width: 980px) {
  .enroll-page__hero,
  .enroll-page__toolbar,
  .notice-item,
  .enroll-course-card__top {
    flex-direction: column;
    align-items: flex-start;
  }
  .enroll-page__toolbar { grid-template-columns: 1fr; }
  .enroll-course-card { grid-template-columns: 1fr; }
  .enroll-course-card__action-row { grid-template-columns: 1fr; }
  .enroll-page__stats { grid-template-columns: 1fr; }
}
</style>
