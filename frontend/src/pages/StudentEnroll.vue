<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import QueryToolbar from "../components/QueryToolbar.vue";
import { getRole } from "../token";

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
const cancelling = ref<number | null>(null);
const courses = ref<EnrollableCourse[]>([]);
const applications = ref<CourseApplication[]>([]);
const notices = ref<Notice[]>([]);
const applyReasonMap = ref<Record<number, string>>({});
const activeTab = ref<"search" | "applications" | "notifications">("search");
const keyword = ref("");
const isPreviewMode = computed(() => String(route.query.preview || "") === "1" && getRole() !== "student");

function searchCourses() {
  activeTab.value = "search";
}

function resetSearch() {
  keyword.value = "";
  activeTab.value = "search";
}

function normalizeStatus(status?: string | null) {
  return String(status || "").trim().toLowerCase();
}

function isJoinedCourse(course: EnrollableCourse) {
  const status = normalizeStatus(course.application_status);
  return status === "linked" || status === "approved";
}

function canApplyCourse(course: EnrollableCourse) {
  return !isPreviewMode.value
    && !course.application_status
    && normalizeStatus(course.enroll_status) === "open"
    && normalizeStatus(course.enrollment_mode) !== "class_auto";
}

function statusLabel(status: string) {
  const value = normalizeStatus(status);
  if (value === "open") return "可报名";
  if (value === "full") return "已满";
  if (value === "closed") return "已关闭";
  if (value === "expired") return "已过期";
  return status;
}

function courseStatusLabel(course: EnrollableCourse) {
  if (isJoinedCourse(course)) return "已报名";
  if (normalizeStatus(course.application_status) === "pending") return "审核中";
  return statusLabel(course.enroll_status);
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
  available: courses.value.filter((course) => !course.application_status && normalizeStatus(course.enroll_status) === "open").length,
  pending: applications.value.filter((item) => normalizeStatus(item.status) === "pending").length,
  unread: notices.value.filter((item) => normalizeStatus(item.status) !== "read").length,
}));

async function loadAll() {
  loading.value = true;
  try {
    if (isPreviewMode.value) {
      const courseRes = await api.get("/admin/courses", { params: { page: 1, page_size: 100 } });
      courses.value = (courseRes.data?.items ?? []).map((item: any) => ({
        id: Number(item.id),
        code: String(item.code || ""),
        title: String(item.title || ""),
        description: String(item.description || ""),
        teacher_name: "",
        max_students: Number(item.max_students || 0),
        enrolled_count: 0,
        apply_deadline: item.apply_deadline || null,
        enroll_status: String(item.enroll_status || ""),
        application_status: null,
        enrollment_mode: "manual_apply",
        target_class: item.target_class || "",
        lifecycle_status: item.lifecycle_status || "",
        start_at: item.start_at || null,
        end_at: item.end_at || null,
      }));
      applications.value = [];
      notices.value = [];
      return;
    }

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
  if (isPreviewMode.value) {
    ElMessage.warning("当前是管理员预览学生端，不能直接提交报名申请");
    return;
  }
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

async function cancelApplication(item: CourseApplication) {
  if (isPreviewMode.value) {
    ElMessage.warning("当前是管理员预览学生端，不能取消报名申请");
    return;
  }
  if (normalizeStatus(item.status) !== "pending") {
    ElMessage.warning("只有审核中的报名申请可以取消");
    return;
  }
  try {
    await ElMessageBox.confirm(`确定取消《${item.course_title}》的报名申请吗？取消后可以重新提交。`, "取消报名", {
      confirmButtonText: "确认取消",
      cancelButtonText: "再想想",
      type: "warning",
    });
  } catch {
    return;
  }
  cancelling.value = item.id;
  try {
    await api.delete(`/enrollment/my/applications/${item.id}`);
    ElMessage.success("已取消报名申请");
    await loadAll();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "取消报名失败");
  } finally {
    cancelling.value = null;
  }
}

async function markRead(noticeId: number) {
  if (isPreviewMode.value) {
    ElMessage.warning("当前是预览模式，不能修改通知状态");
    return;
  }
  try {
    await api.post(`/enrollment/my/notifications/${noticeId}/read`);
    notices.value = notices.value.map((item) => (item.id === noticeId ? { ...item, status: "READ" } : item));
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新通知状态失败");
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
        <h1>先找到课程，再决定要不要加入</h1>
        <p>把课程搜索、申请记录和站内通知收成三个简单分区，减少原来偏后台化的复杂布局。</p>
      </div>

      <div class="enroll-page__hero-panel">
        <span>当前视图</span>
        <strong>{{ activeTab === "search" ? "课程搜索" : activeTab === "applications" ? "报名记录" : "站内通知" }}</strong>
        <p>先搜索课程；提交后到报名记录查看状态；有新消息时在通知里统一处理。</p>
        <div class="enroll-page__hero-actions">
          <el-button @click="goBackStudy">返回学习中心</el-button>
          <el-button type="primary" @click="loadAll">刷新</el-button>
        </div>
      </div>
    </section>

    <section class="enroll-page__stats">
      <article class="enroll-page__stat-card"><span>可报名课程</span><strong>{{ stats.available }}</strong></article>
      <article class="enroll-page__stat-card"><span>待审核申请</span><strong>{{ stats.pending }}</strong></article>
      <article class="enroll-page__stat-card"><span>未读通知</span><strong>{{ stats.unread }}</strong></article>
    </section>

    <section class="enroll-page__tab-strip">
      <button class="enroll-page__tab-pill" :class="{ active: activeTab === 'search' }" @click="activeTab = 'search'">课程搜索</button>
      <button class="enroll-page__tab-pill" :class="{ active: activeTab === 'applications' }" @click="activeTab = 'applications'">报名记录</button>
      <button class="enroll-page__tab-pill" :class="{ active: activeTab === 'notifications' }" @click="activeTab = 'notifications'">站内通知</button>
    </section>

    <template v-if="activeTab === 'search'">
      <section class="enroll-page__toolbar panel-card">
        <QueryToolbar
          v-model="keyword"
          placeholder="请输入课程名称、课程代码或教师姓名"
          hint="请输入课程名称、课程代码或教师姓名"
          input-width="520px"
          @search="searchCourses"
          @reset="resetSearch"
        />
      </section>

      <section class="enroll-page__list">
        <article v-for="course in filteredCourses" :key="course.id" class="enroll-course-card panel-card">
          <div class="enroll-course-card__top">
            <div class="enroll-course-card__title-block">
              <strong>{{ course.title }}</strong>
              <p>{{ course.code }} · {{ course.teacher_name || "未分配教师" }}</p>
            </div>
            <el-tag round>{{ appStatusLabel(course.application_status) }}</el-tag>
          </div>

          <div class="enroll-course-card__chips">
            <span>{{ courseStatusLabel(course) }}</span>
            <span>名额 {{ course.enrolled_count }}/{{ course.max_students }}</span>
            <span v-if="course.target_class">班级 {{ course.target_class }}</span>
          </div>

          <p class="enroll-course-card__desc">{{ course.description || autoJoinHint(course) }}</p>
          <p class="enroll-course-card__meta">{{ autoJoinHint(course) }}</p>

          <div class="enroll-course-card__apply">
            <div class="enroll-course-card__reason-head">
              <span class="enroll-course-card__reason-label">申请理由（可选）</span>
              <span class="enroll-course-card__reason-tip">可留空，直接提交即可</span>
            </div>
            <div class="enroll-course-card__action-row">
              <el-input
                v-model="applyReasonMap[course.id]"
                placeholder="可填写申请原因，例如补修、跟班学习或课程需要"
                :disabled="!canApplyCourse(course)"
              />
              <el-button
                type="primary"
                plain
                :loading="applying === course.id"
                :disabled="!canApplyCourse(course)"
                @click="applyCourse(course)"
              >
                {{ isJoinedCourse(course) ? "已报名" : normalizeStatus(course.enrollment_mode) === "class_auto" ? "自动关联课程" : "申请加入" }}
              </el-button>
            </div>
          </div>
        </article>
        <el-empty v-if="filteredCourses.length === 0" description="暂时没有匹配到课程" />
      </section>
    </template>

    <section v-else-if="activeTab === 'applications'" class="panel-card enroll-records-card">
      <header class="enroll-table-card__head">
        <h3>我的报名记录</h3>
        <span>共 {{ applications.length }} 条</span>
      </header>

      <div v-if="applications.length === 0" class="empty">暂时还没有报名记录</div>
      <div v-else class="enroll-records-list">
        <article v-for="item in applications" :key="item.id" class="enroll-record-item">
          <div class="enroll-record-item__top">
            <div>
              <strong>{{ item.course_title }}</strong>
              <p>{{ item.created_at.replace('T', ' ').slice(0, 16) }}</p>
            </div>
            <div class="enroll-record-item__status">
              <el-tag round>{{ appStatusLabel(item.status) }}</el-tag>
              <el-button
                v-if="normalizeStatus(item.status) === 'pending'"
                size="small"
                plain
                type="danger"
                :loading="cancelling === item.id"
                @click="cancelApplication(item)"
              >
                取消报名
              </el-button>
            </div>
          </div>

          <div class="enroll-record-item__grid">
            <div>
              <span>申请理由</span>
              <p>{{ item.apply_reason || "未填写" }}</p>
            </div>
            <div>
              <span>审核备注</span>
              <p>{{ item.review_remark || item.reject_reason || "暂时没有反馈" }}</p>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section v-else class="panel-card enroll-table-card">
      <header class="enroll-table-card__head">
        <h3>站内通知</h3>
        <span>未读 {{ stats.unread }}</span>
      </header>
      <div v-if="notices.length === 0" class="empty">暂时没有通知</div>
      <div v-else class="notice-list">
        <div v-for="notice in notices" :key="notice.id" class="notice-item">
          <div>
            <strong>{{ notice.title }}</strong>
            <p>{{ notice.content }}</p>
            <small>{{ notice.created_at.replace('T', ' ').slice(0, 16) }}</small>
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
.enroll-page {
  --enroll-theme-surface: #ffffff;
  --enroll-theme-surface-soft: #f8fafc;
  --enroll-theme-surface-muted: #f1f5f9;
  --enroll-theme-surface-accent: #eefbf3;
  --enroll-theme-border: rgba(148, 163, 184, 0.22);
  --enroll-theme-border-strong: rgba(34, 197, 94, 0.26);
  --enroll-theme-ink-soft: #64748b;
  display: grid;
  gap: 18px;
  padding-bottom: 12px;
}

.enroll-page__hero,
.enroll-page__toolbar,
.enroll-course-card,
.enroll-page__stat-card,
.enroll-table-card,
.enroll-records-card,
.enroll-page__tab-strip {
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}

.enroll-page__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 18px;
  padding: 22px 24px;
  background:
    radial-gradient(circle at top left, rgba(219, 234, 254, 0.42), transparent 30%),
    radial-gradient(circle at right bottom, rgba(220, 252, 231, 0.22), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.enroll-page__hero-copy {
  display: grid;
  gap: 8px;
  max-width: 620px;
}

.enroll-page__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eefbf3;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: none;
  color: #166534;
  border: 1px solid rgba(34, 197, 94, 0.18);
}

.enroll-page__hero h1 {
  margin: 0;
  font-size: 0;
  line-height: 0;
  letter-spacing: 0;
}

.enroll-page__hero-copy h1::before {
  content: "课程加入";
  display: block;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.05;
  letter-spacing: -0.04em;
  color: #1f2937;
}

.enroll-page__hero p {
  margin: 0;
  color: var(--enroll-theme-ink-soft);
}

.enroll-page__hero-copy > p {
  font-size: 0;
  line-height: 0;
}

.enroll-page__hero-copy > p::before {
  content: "搜索课程，提交申请，查看状态";
  display: block;
  font-size: 14px;
  line-height: 1.6;
}

.enroll-page__hero-panel > p {
  font-size: 0;
  line-height: 0;
}

.enroll-page__hero-panel > p::before {
  content: "先搜索，再申请";
  display: block;
  font-size: 14px;
  line-height: 1.6;
}

.enroll-page__hero-panel {
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid var(--enroll-theme-border);
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, var(--enroll-theme-surface-soft) 100%);
}

.enroll-page__hero-panel span,
.enroll-page__stat-card span,
.enroll-record-item__grid span {
  font-size: 12px;
  font-weight: 700;
  color: var(--enroll-theme-ink-soft);
}

.enroll-page__hero-panel strong {
  font-size: 20px;
  color: #1f2937;
}

.enroll-page__hero-panel :deep(.el-select__wrapper) {
  min-height: 42px;
  border-radius: 14px;
  background: var(--enroll-theme-surface-soft) !important;
  box-shadow: 0 0 0 1px var(--enroll-theme-border) inset !important;
}

.enroll-page__hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.enroll-page__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.enroll-page__stat-card {
  padding: 18px 20px;
  display: grid;
  gap: 8px;
  min-height: 96px;
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, var(--enroll-theme-surface-soft) 100%);
}

.enroll-page__stat-card strong {
  font-size: 30px;
  color: #1f2937;
  line-height: 1;
}

.enroll-page__tab-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px;
}

.enroll-page__tab-pill {
  border: 1px solid var(--enroll-theme-border);
  background: var(--enroll-theme-surface);
  color: #475569;
  border-radius: 999px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, background-color 0.18s ease;
}

.enroll-page__tab-pill.active {
  background: #eefbf3;
  color: #166534;
  border-color: var(--enroll-theme-border-strong);
}

.enroll-page__toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  padding: 16px;
  align-items: stretch;
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, #f8fafc 100%);
}

.enroll-page__list,
.notice-list,
.enroll-records-list {
  display: grid;
  gap: 12px;
}

.enroll-course-card {
  padding: 20px 22px;
  display: grid;
  gap: 14px;
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, #f8fafc 100%);
}

.enroll-course-card__top,
.enroll-record-item__top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.enroll-record-item__status {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.enroll-course-card__title-block {
  display: grid;
  gap: 4px;
}

.enroll-course-card__top strong,
.notice-item strong,
.enroll-record-item__top strong {
  font-size: 18px;
  color: #1f2937;
}

.enroll-page :deep(.el-tag) {
  border-color: var(--enroll-theme-border);
  background: var(--enroll-theme-surface-soft);
  color: #475569;
}

.enroll-course-card__top p,
.enroll-course-card__desc,
.notice-item p,
.notice-item small {
  margin: 0;
  color: var(--enroll-theme-ink-soft);
  line-height: 1.6;
}

.enroll-course-card__desc {
  font-size: 14px;
}

.enroll-course-card__meta {
  font-size: 12px;
  color: var(--enroll-theme-ink-soft);
  line-height: 1.6;
}

.enroll-course-card__chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.enroll-course-card__chips span {
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--enroll-theme-border);
  background: var(--enroll-theme-surface-soft);
  font-size: 12px;
  color: #475569;
}

.enroll-course-card__apply {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--enroll-theme-border);
  background: linear-gradient(180deg, var(--enroll-theme-surface-soft) 0%, var(--enroll-theme-surface) 100%);
}

.enroll-course-card__reason-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
}

.enroll-course-card__reason-label {
  font-size: 12px;
  font-weight: 800;
  color: #1f2937;
}

.enroll-course-card__reason-tip {
  font-size: 12px;
  color: var(--app-text-light);
}

.enroll-course-card__action-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}

.enroll-course-card__apply :deep(.el-input__wrapper) {
  border-radius: 14px;
  min-height: 42px;
  background: var(--enroll-theme-surface-soft) !important;
  box-shadow: 0 0 0 1px var(--enroll-theme-border) inset !important;
}

.enroll-course-card__apply :deep(.el-button) {
  border-radius: 14px;
  min-height: 42px;
  padding-inline: 18px;
}

.enroll-page__hero-actions :deep(.el-button),
.enroll-course-card__apply :deep(.el-button:not(.el-button--primary)),
.enroll-page__toolbar :deep(.query-toolbar__btn:not(.query-toolbar__btn--primary)) {
  border-color: var(--enroll-theme-border);
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, var(--enroll-theme-surface-soft) 100%);
  color: #475569;
}

.enroll-page__hero-actions :deep(.el-button--primary),
.enroll-course-card__apply :deep(.el-button--primary),
.enroll-page__toolbar :deep(.query-toolbar__btn--primary) {
  border-color: var(--enroll-theme-border-strong);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.enroll-page__toolbar :deep(.query-toolbar__search .el-input__wrapper) {
  background: var(--enroll-theme-surface-soft) !important;
  box-shadow: 0 0 0 1px var(--enroll-theme-border) inset !important;
}

.enroll-page__toolbar :deep(.query-toolbar__search .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #60a5fa inset, 0 0 0 4px rgba(96, 165, 250, 0.14) !important;
}

.enroll-page__toolbar :deep(.query-toolbar__search .el-input__prefix-inner),
.enroll-page__toolbar :deep(.query-toolbar__search .el-input__inner::placeholder) {
  color: var(--enroll-theme-ink-soft);
}

.enroll-table-card,
.enroll-records-card {
  padding: 18px 20px;
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, var(--enroll-theme-surface-soft) 100%);
}

.enroll-table-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.enroll-table-card__head h3 {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
}

.enroll-table-card__head span {
  color: var(--enroll-theme-ink-soft);
  font-size: 13px;
}

.enroll-record-item,
.notice-item {
  display: grid;
  gap: 12px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid var(--enroll-theme-border);
  background: linear-gradient(180deg, var(--enroll-theme-surface) 0%, var(--enroll-theme-surface-soft) 100%);
}

.enroll-record-item__top p {
  margin: 4px 0 0;
  color: var(--enroll-theme-ink-soft);
  font-size: 13px;
}

.enroll-record-item__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.enroll-record-item__grid p {
  margin: 4px 0 0;
  color: var(--enroll-theme-ink-soft);
  line-height: 1.6;
}

.notice-item {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.empty {
  color: var(--enroll-theme-ink-soft);
  padding: 6px 0;
}

.enroll-page__hero-copy h1::before {
  content: "课程加入";
}

.enroll-page__hero-copy > p::before {
  content: "搜索课程，提交申请，查看状态";
}

.enroll-page__hero-panel > p::before {
  content: "先搜索，再申请";
}

@media (max-width: 980px) {
  .enroll-page__hero,
  .enroll-page__stats,
  .enroll-record-item__grid,
  .notice-item {
    grid-template-columns: 1fr;
  }

  .enroll-course-card__top,
  .enroll-record-item__top,
  .enroll-course-card__reason-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .enroll-course-card__action-row {
    grid-template-columns: 1fr;
  }
}
</style>
