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
const joinCodeInput = ref("");
const joinByCodeLoading = ref(false);
const activeTab = ref<"join" | "applications" | "notifications">("join");
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
  if (normalizeStatus(course.enrollment_mode) === "class_auto") return `系统会按班级 ${course.target_class || ""} 自动关联，也可使用课程代码加入。`;
  if (normalizeStatus(course.enroll_status) !== "open") return "当前不在开放报名时间。";
  return "优先使用课程代码加入；只有无法自动匹配时再提交申请。";
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

async function joinByCourseCode() {
  const code = joinCodeInput.value.trim();
  if (!code) {
    ElMessage.warning("请先输入课程代码");
    return;
  }
  joinByCodeLoading.value = true;
  try {
    const res = await api.post("/enrollment/courses/join-by-code", { join_code: code });
    const title = res.data?.title || "";
    if (res.data?.already_enrolled) {
      ElMessage.success(title ? `你已在《${title}》中` : "你已加入该课程");
    } else {
      ElMessage.success(title ? `已加入《${title}》` : "加入成功");
    }
    joinCodeInput.value = "";
    await loadAll();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加入失败");
  } finally {
    joinByCodeLoading.value = false;
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
      <div>
        <span class="enroll-page__eyebrow">课程加入</span>
        <h1>先用课程代码加入，再看申请记录和站内通知</h1>
        <p>这个页面只处理课程加入、报名记录和通知，不再堆长篇说明。</p>
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
      <el-tab-pane name="join" label="加入课程">
        <section class="enroll-page__toolbar panel-card">
          <div class="enroll-page__join-box">
            <el-input v-model="joinCodeInput" placeholder="输入课程代码" clearable style="max-width: 320px" />
            <el-button type="primary" :loading="joinByCodeLoading" @click="joinByCourseCode">加入课程</el-button>
          </div>
          <el-input v-model="keyword" placeholder="搜索课程名称 / 代码 / 教师" clearable style="max-width: 280px" />
        </section>

        <section class="enroll-page__list">
          <article v-for="course in filteredCourses" :key="course.id" class="enroll-course-card panel-card">
            <div class="enroll-course-card__main">
              <div class="enroll-course-card__top">
                <div>
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
              <p class="enroll-course-card__hint">{{ autoJoinHint(course) }}</p>
            </div>
            <div class="enroll-course-card__actions">
              <el-input
                v-model="applyReasonMap[course.id]"
                placeholder="选填：申请理由"
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
.enroll-page { display: grid; gap: 18px; }
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
  gap: 16px;
  padding: 24px 26px;
  background: linear-gradient(135deg, #eef4ff 0%, #f6fbff 48%, #ffffff 100%);
}
.enroll-page__eyebrow { font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--app-primary-deep); }
.enroll-page__hero h1 { margin: 8px 0 0; font-size: 28px; color: var(--app-text-main); }
.enroll-page__hero p { margin: 10px 0 0; line-height: 1.7; color: var(--app-text-soft); }
.enroll-page__hero-actions, .enroll-page__join-box, .enroll-course-card__actions { display: flex; gap: 10px; flex-wrap: wrap; }
.enroll-page__stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.enroll-page__stat-card { padding: 18px; display: grid; gap: 8px; }
.enroll-page__stat-card span { font-size: 12px; color: var(--app-text-soft); }
.enroll-page__stat-card strong { font-size: 26px; color: var(--app-text-main); }
.enroll-page__toolbar { display: flex; justify-content: space-between; gap: 14px; padding: 18px 20px; margin-bottom: 14px; }
.enroll-page__list, .notice-list { display: grid; gap: 12px; }
.enroll-course-card { padding: 18px 20px; display: grid; gap: 14px; }
.enroll-course-card__top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.enroll-course-card__top strong { font-size: 18px; color: var(--app-text-main); }
.enroll-course-card__top p, .enroll-course-card__desc, .enroll-course-card__hint, .notice-item p, .notice-item small { margin: 0; color: var(--app-text-soft); line-height: 1.6; }
.enroll-course-card__chips { display: flex; gap: 8px; flex-wrap: wrap; }
.enroll-course-card__chips span { padding: 5px 10px; border-radius: 999px; border: 1px solid #dbe6f2; background: #f8fbff; font-size: 12px; color: #58718f; }
.enroll-course-card__hint { font-size: 13px; }
.enroll-course-card__actions { align-items: center; }
.enroll-course-card__actions :deep(.el-input) { flex: 1 1 240px; }
.enroll-table-card { padding: 18px 20px; }
.enroll-table-card__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.enroll-table-card__head h3 { margin: 0; font-size: 18px; color: var(--app-text-main); }
.enroll-table-card__head span { color: var(--app-text-soft); font-size: 13px; }
.notice-item { border: 1px solid var(--app-border); border-radius: 16px; padding: 16px; display: flex; justify-content: space-between; gap: 14px; align-items: center; background: #fcfdff; }
.empty { color: #7c8da2; padding: 6px 0; }
@media (max-width: 980px) {
  .enroll-page__hero,
  .enroll-page__toolbar,
  .notice-item,
  .enroll-course-card__top {
    flex-direction: column;
    align-items: flex-start;
  }
  .enroll-page__stats { grid-template-columns: 1fr; }
}
</style>
