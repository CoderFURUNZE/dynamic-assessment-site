<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const props = withDefaults(defineProps<{ subject: string; grade: string; showStudentDetailAction?: boolean }>(), {
  showStudentDetailAction: false,
});
const emit = defineEmits<{
  (e: "view-student", userId: number): void;
}>();

type StageSummary = {
  stage_id: number;
  stage_title: string;
  stage_order: number;
  student_count: number;
  avg_dynamic_score: number;
  avg_course_mastery: number;
  risk_count: number;
  progress_count: number;
  steady_count: number;
  regress_count: number;
};

const loading = ref(false);
const data = ref({
  total_students: 0,
  persona_distribution: [] as Array<{ persona_label: string; count: number }>,
  stage_summary: [] as StageSummary[],
  latest_stage: null as StageSummary | null,
  risk_students: [] as Array<Record<string, any>>,
  weak_kps: [] as Array<Record<string, any>>,
  progress_ranking: [] as Array<Record<string, any>>,
});

const stageCount = computed(() => data.value.stage_summary.length);
const latestStageScore = computed(() => Math.round(((data.value.latest_stage?.avg_dynamic_score ?? 0) * 100)));
const latestStageMastery = computed(() => Math.round(((data.value.latest_stage?.avg_course_mastery ?? 0) * 100)));

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const res = await api.get(
      `/admin/analytics/overview?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    data.value = res.data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载学习分析失败");
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.subject, props.grade],
  () => load(),
  { immediate: true }
);
</script>

<template>
  <div class="analytics-shell" v-loading="loading">
    <div class="analytics-metrics">
      <el-card shadow="never">
        <div class="metric-label">班级学生数</div>
        <div class="metric-value">{{ data.total_students }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="metric-label">阶段数量</div>
        <div class="metric-value">{{ stageCount }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="metric-label">风险学生数</div>
        <div class="metric-value">{{ data.risk_students.length }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="metric-label">最新阶段均分</div>
        <div class="metric-value">{{ latestStageScore }}%</div>
      </el-card>
      <el-card shadow="never">
        <div class="metric-label">最新阶段掌握度</div>
        <div class="metric-value">{{ latestStageMastery }}%</div>
      </el-card>
      <el-card shadow="never">
        <div class="metric-label">薄弱知识点数</div>
        <div class="metric-value">{{ data.weak_kps.length }}</div>
      </el-card>
    </div>

    <div class="analytics-grid">
      <el-card class="panel-card" shadow="never">
        <template #header>学习者类型分布</template>
        <div class="distribution-list">
          <div v-for="item in data.persona_distribution" :key="item.persona_label" class="distribution-item">
            <span>{{ item.persona_label }}</span>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>班级阶段分析</template>
        <div v-if="data.stage_summary.length" class="stage-summary-list">
          <div v-for="item in data.stage_summary" :key="item.stage_id" class="stage-summary-item">
            <div class="stage-summary-item__head">
              <div>
                <div class="stage-summary-item__index">阶段 {{ item.stage_order }}</div>
                <div class="stage-summary-item__title">{{ item.stage_title }}</div>
              </div>
              <el-tag size="small">{{ item.student_count }} 人</el-tag>
            </div>
            <div class="stage-summary-item__metrics">
              <span>均分 {{ Math.round((item.avg_dynamic_score || 0) * 100) }}%</span>
              <span>掌握 {{ Math.round((item.avg_course_mastery || 0) * 100) }}%</span>
            </div>
            <div class="stage-summary-item__trend">
              <span class="trend-pill trend-pill--up">进步 {{ item.progress_count }}</span>
              <span class="trend-pill trend-pill--steady">持平 {{ item.steady_count }}</span>
              <span class="trend-pill trend-pill--down">退步 {{ item.regress_count }}</span>
              <span class="trend-pill trend-pill--risk">风险 {{ item.risk_count }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="当前还没有阶段评价数据" />
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>薄弱知识点 Top10</template>
        <el-table :data="data.weak_kps" size="small">
          <el-table-column prop="code" label="编码" width="120" />
          <el-table-column prop="title" label="知识点" min-width="180" />
          <el-table-column prop="avg_mastery" label="平均掌握度" width="120">
            <template #default="{ row }">
              {{ Math.round((row.avg_mastery || 0) * 100) }}%
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>风险学生清单</template>
        <el-table :data="data.risk_students" size="small">
          <el-table-column prop="username" label="账号" width="120" />
          <el-table-column prop="full_name" label="姓名" width="100" />
          <el-table-column prop="persona_label" label="类型" width="140" />
          <el-table-column prop="latest_stage_title" label="最新阶段" width="140" />
          <el-table-column prop="stage_trend" label="变化" width="90" />
          <el-table-column prop="risk_level" label="等级" width="90" />
          <el-table-column prop="reason_summary" label="原因" min-width="220" />
          <el-table-column v-if="props.showStudentDetailAction" label="详情" width="100">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="emit('view-student', row.user_id)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>学习进度排行</template>
        <el-table :data="data.progress_ranking" size="small">
          <el-table-column prop="username" label="账号" width="120" />
          <el-table-column prop="full_name" label="姓名" width="100" />
          <el-table-column prop="persona_label" label="类型" width="140" />
          <el-table-column prop="latest_stage_title" label="最新阶段" width="140" />
          <el-table-column prop="stage_trend" label="变化" width="90" />
          <el-table-column prop="course_mastery" label="课程掌握度" width="120">
            <template #default="{ row }">
              {{ Math.round((row.course_mastery || 0) * 100) }}%
            </template>
          </el-table-column>
          <el-table-column prop="dynamic_score" label="动态评分" width="120">
            <template #default="{ row }">
              {{ Math.round((row.dynamic_score || 0) * 100) }}%
            </template>
          </el-table-column>
          <el-table-column v-if="props.showStudentDetailAction" label="详情" width="100">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="emit('view-student', row.user_id)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.analytics-shell {
  display: grid;
  gap: 16px;
}

.analytics-metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.metric-label {
  font-size: 12px;
  color: #5a7797;
}

.metric-value {
  margin-top: 6px;
  font-size: 24px;
  font-weight: 600;
  color: var(--app-ink);
}

.analytics-grid {
  display: grid;
  gap: 16px;
}

.distribution-list,
.stage-summary-list {
  display: grid;
  gap: 10px;
}

.distribution-item,
.stage-summary-item {
  padding: 12px 14px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e1eaf1;
}

.distribution-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stage-summary-item {
  display: grid;
  gap: 10px;
}

.stage-summary-item__head,
.stage-summary-item__metrics,
.stage-summary-item__trend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.stage-summary-item__index {
  font-size: 12px;
  color: #5b7797;
}

.stage-summary-item__title {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--app-ink);
}

.stage-summary-item__metrics {
  font-size: 12px;
  color: #62809d;
}

.stage-summary-item__trend {
  gap: 8px;
}

.trend-pill {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.trend-pill--up {
  background: #e8f8ef;
  color: #1f8a52;
}

.trend-pill--steady {
  background: #eef4fb;
  color: #4c6f93;
}

.trend-pill--down,
.trend-pill--risk {
  background: #fff0e8;
  color: #c96a2b;
}

@media (max-width: 1200px) {
  .analytics-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .analytics-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
