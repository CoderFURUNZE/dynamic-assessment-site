<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminIntroHero from "../components/AdminIntroHero.vue";
import QueryToolbar from "../components/QueryToolbar.vue";

type AuditItem = {
  id: number;
  actor: string;
  role: string;
  action: string;
  detail: string;
  created_at: string;
};

const loading = ref(false);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const items = ref<AuditItem[]>([]);
const keyword = ref("");

const auditActionLabelMap: Record<string, string> = {
  seed_full: "完整初始化演示数据",
  seed_demo: "生成演示课程数据",
  questions_import_docx: "导入题库文档",
  user_create: "新增用户",
  user_update: "更新用户",
  user_delete: "删除用户",
  course_create: "新增课程",
  course_update: "更新课程",
  course_delete: "删除课程",
  kp_delete: "删除知识点",
  kp_video_bind_bilibili: "绑定哔哩哔哩视频",
  kp_video_clear: "清空知识点视频",
  kp_video_upload_local: "上传本地视频",
  kp_video_bind_url: "绑定外部视频链接",
  kp_resource_upload: "上传知识点资源",
  kp_resource_create: "新增知识点资源",
  kp_resource_update: "更新知识点资源",
  kp_resource_delete: "删除知识点资源",
  kp_task_create: "新增知识点任务",
  kp_task_update: "更新知识点任务",
  kp_task_delete: "删除知识点任务",
  persona_rule_update: "更新画像规则",
  persona_recalculate: "重算学生画像",
  persona_override_set: "设置人工画像",
  persona_override_delete: "删除人工画像",
  stage_feedback_save: "保存阶段反馈",
  course_stage_create: "新增课程阶段",
  course_stage_update: "更新课程阶段",
  course_stage_delete: "删除课程阶段",
};

const auditDetailKeyLabelMap: Record<string, string> = {
  created_kp: "新增知识点",
  created_questions: "新增题目",
  created_enrollments: "新增选课记录",
  subject: "学科",
  grade: "年级",
  count: "数量",
  user_id: "用户 ID",
  stage_id: "阶段 ID",
  course_id: "课程 ID",
  teacher_id: "教师 ID",
  kp_id: "知识点 ID",
  task_id: "任务 ID",
  resource_id: "资源 ID",
  username: "用户名",
  role: "角色",
  code: "课程编码",
  title: "课程名称",
  id: "ID",
  persona: "画像类型",
  bvid: "视频编号",
  page: "分 P",
  deleted: "删除数量",
  file: "文件名",
  url: "链接",
  type: "类型",
  created: "新增数量",
  skipped: "跳过数量",
  errors: "错误数量",
};

const roleLabelMap: Record<string, string> = {
  admin: "管理员",
  teacher: "教师",
  student: "学生",
  system: "系统",
};

const personaLabelMap: Record<string, string> = {
  smart_capable: "高潜能型",
  diligent: "勤奋型",
  struggling_persistent: "吃苦坚持型",
  procrastinating_risk: "拖延风险型",
  steady_progress: "稳步进步型",
};

function formatAuditAction(action: string) {
  return auditActionLabelMap[action] ?? action.replace(/_/g, " / ");
}

function parseDetailPairs(detail: string) {
  const pairs: Array<{ key: string; value: string }> = [];
  const pattern = /([a-zA-Z_]+)=([^=]+?)(?=\s+[a-zA-Z_]+=|$)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(detail)) !== null) {
    pairs.push({ key: match[1], value: match[2].trim() });
  }
  return pairs;
}

function formatDetailValue(key: string, value: string) {
  if (key === "role") {
    return roleLabelMap[value] ?? value;
  }
  if (key === "persona") {
    return personaLabelMap[value] ?? value;
  }
  return value;
}

function formatAuditDetail(detail: string) {
  if (!detail.trim()) {
    return "无详细说明";
  }

  const pairs = parseDetailPairs(detail);
  if (!pairs.length) {
    return detail;
  }

  return pairs
    .map(({ key, value }) => {
      const label = auditDetailKeyLabelMap[key] ?? key;
      const formattedValue = formatDetailValue(key, value);
      if (/^(created_kp|created_questions|created_enrollments|count|deleted|created|skipped|errors)$/.test(key)) {
        return `${label} ${formattedValue} 个`;
      }
      return `${label}：${formattedValue}`;
    })
    .join("，");
}

async function load() {
  loading.value = true;
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize.value),
    });
    if (keyword.value.trim()) {
      params.set("keyword", keyword.value.trim());
    }
    const res = await api.get(`/admin/audit?${params.toString()}`);
    items.value = res.data?.items ?? [];
    total.value = Number(res.data?.total ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载审计日志失败");
  } finally {
    loading.value = false;
  }
}

function search() {
  page.value = 1;
  load();
}

function resetSearch() {
  if (!keyword.value.trim()) return;
  keyword.value = "";
  page.value = 1;
  load();
}

onMounted(load);
</script>

<template>
  <div class="audit-page">
    <AdminIntroHero eyebrow="平台概览" title="审计日志" pill="关键操作" />

    <section class="audit-page__panel panel-card" v-loading="loading">
      <div class="audit-page__table-wrap">
        <div class="audit-page__table-header">
          <div class="audit-page__table-title-wrap">
            <div class="audit-page__table-title">审计列表</div>
            <QueryToolbar
              v-model="keyword"
              placeholder="请输入操作人、角色、动作或详情"
              hint="请输入操作人、角色、动作或详情"
              input-width="520px"
              @search="search"
              @reset="resetSearch"
            />
          </div>
          <div class="audit-page__table-total">共 {{ total }} 条</div>
        </div>

        <el-table :data="items" size="small" border class="audit-page__table">
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 19) }}</template>
          </el-table-column>
          <el-table-column prop="actor" label="操作人" width="120" />
          <el-table-column prop="role" label="角色" width="100" />
          <el-table-column prop="action" label="动作" width="220">
            <template #default="{ row }">{{ formatAuditAction(row.action) }}</template>
          </el-table-column>
          <el-table-column prop="detail" label="详情" min-width="420" show-overflow-tooltip>
            <template #default="{ row }">{{ formatAuditDetail(row.detail) }}</template>
          </el-table-column>
        </el-table>

        <div class="audit-page__pager">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            layout="total, prev, pager, next"
            :total="total"
            @current-change="load"
          />
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.audit-page {
  display: grid;
  gap: 20px;
}

.audit-page__panel {
  padding: 18px 18px 16px;
}

.audit-page__table-wrap {
  display: grid;
  gap: 14px;
  padding: 0;
}

.audit-page__table-wrap :deep(.query-toolbar) {
  padding: 14px 16px;
  border: 1px solid #dfe9f7;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.audit-page__table-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 0 2px 12px;
}

.audit-page__table-title-wrap {
  display: grid;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.audit-page__table-title {
  font-size: 18px;
  font-weight: 800;
  color: #1f3556;
}

.audit-page__table-title-wrap :deep(.query-toolbar) {
  width: auto;
  max-width: 760px;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.audit-page__table-total {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: #f3f8ff;
  border: 1px solid #dce8f7;
  color: #37537d;
  font-size: 13px;
  font-weight: 700;
}

.audit-page__table-wrap :deep(.el-table) {
  border-radius: 0 !important;
  overflow: visible;
  box-shadow: none !important;
  border: none !important;
  background: #ffffff !important;
}

.audit-page__table-wrap :deep(.el-table__inner-wrapper) {
  border-radius: 0;
}

.audit-page__table-wrap :deep(.el-table__border-left-patch) {
  display: none !important;
}

.audit-page__table-wrap :deep(.el-table::before),
.audit-page__table-wrap :deep(.el-table--border::before),
.audit-page__table-wrap :deep(.el-table--border::after) {
  display: none !important;
}

.audit-page__table-wrap :deep(.el-table th.el-table__cell) {
  background: #f6faff !important;
  color: #587394;
  font-weight: 800;
}

.audit-page__table-wrap :deep(.el-table td.el-table__cell),
.audit-page__table-wrap :deep(.el-table th.el-table__cell) {
  padding-top: 16px;
  padding-bottom: 16px;
  border-right: 1px solid #edf3fb !important;
  border-bottom: 1px solid #edf3fb !important;
}

.audit-page__table-wrap :deep(.el-table tr td:last-child),
.audit-page__table-wrap :deep(.el-table tr th:last-child) {
  border-right: none !important;
}

.audit-page__table-wrap :deep(.el-table__row:last-child td.el-table__cell) {
  border-bottom: none !important;
}

.audit-page__table-wrap :deep(.el-table__row:hover > td.el-table__cell) {
  background: #f8fbff !important;
}

.audit-page__table-wrap :deep(.el-table .cell) {
  white-space: normal;
  color: #274263;
}

.audit-page__table-wrap :deep(.el-table__empty-block) {
  min-height: 120px;
  background: #ffffff;
}

.audit-page__table-wrap :deep(.el-table__empty-text) {
  color: #8b9ab0;
}

.audit-page__pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 0;
}

@media (max-width: 768px) {
  .audit-page__table-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .audit-page__table-title-wrap :deep(.query-toolbar) {
    max-width: 100%;
    width: 100%;
  }
}
</style>
