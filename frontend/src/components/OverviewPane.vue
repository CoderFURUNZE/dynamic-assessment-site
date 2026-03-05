<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const props = defineProps<{ subject: string; grade: string }>();

type Summary = {
  total_kps: number;
  mastered: number;
  in_progress: number;
  not_mastered: number;
  avg_mastery: number;
};
type MasteryItem = { kp_id: number; code: string; title: string; mastery: number };
type Recent = {
  last_practice_at?: string | null;
  last_quiz_at?: string | null;
  last_video_at?: string | null;
  last_expression_at?: string | null;
};
type Practice7d = { total: number; correct: number; accuracy: number };

const loading = ref(false);
const summary = ref<Summary>({
  total_kps: 0,
  mastered: 0,
  in_progress: 0,
  not_mastered: 0,
  avg_mastery: 0,
});
const masteryMap = ref<MasteryItem[]>([]);
const weakPoints = ref<MasteryItem[]>([]);
const recent = ref<Recent>({});
const practice7d = ref<Practice7d>({ total: 0, correct: 0, accuracy: 0 });
const reviewDue = ref(0);

const avgPercent = computed(() => Math.round((summary.value.avg_mastery || 0) * 100));
const hasKps = computed(() => masteryMap.value.length > 0);

function formatTime(value?: string | null) {
  if (!value) return "暂无";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function masteryColor(value: number) {
  if (value >= 0.85) return "#6aa7ff";
  if (value >= 0.5) return "#4f8cff";
  return "#2f6fd6";
}

async function load() {
  loading.value = true;
  try {
    const res = await api.get(
      `/eval/overview?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    summary.value = res.data.summary ?? summary.value;
    masteryMap.value = res.data.mastery_map ?? [];
    weakPoints.value = res.data.weak_points ?? [];
    recent.value = res.data.recent_activity ?? {};
    practice7d.value = res.data.practice_7d ?? practice7d.value;
    reviewDue.value = Number(res.data.review_due ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载总览失败");
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
  <el-card class="panel-card">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>学习总览</div>
        <el-button size="small" @click="load" :loading="loading">刷新</el-button>
      </div>
    </template>

    <div v-if="loading">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else>
      <div style="display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));">
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">知识点总数</div>
          <div style="font-weight: 700; font-size: 22px">{{ summary.total_kps }}</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">已掌握</div>
          <div style="font-weight: 700; font-size: 22px">{{ summary.mastered }}</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">进行中</div>
          <div style="font-weight: 700; font-size: 22px">{{ summary.in_progress }}</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">待巩固</div>
          <div style="font-weight: 700; font-size: 22px">{{ summary.not_mastered }}</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">平均掌握度</div>
          <div style="font-weight: 700; font-size: 22px">{{ avgPercent }}%</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">待复习任务</div>
          <div style="font-weight: 700; font-size: 22px">{{ reviewDue }}</div>
        </el-card>
      </div>

      <div style="margin-top: 12px; display: grid; gap: 12px; grid-template-columns: minmax(260px, 1fr) minmax(260px, 1fr);">
        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">本周练习表现</div>
          <div style="display: grid; gap: 6px">
            <el-text>练习次数：{{ practice7d.total }}</el-text>
            <el-text>正确次数：{{ practice7d.correct }}</el-text>
            <el-text>正确率：{{ Math.round((practice7d.accuracy || 0) * 100) }}%</el-text>
          </div>
        </el-card>
        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">最近活动</div>
          <div style="display: grid; gap: 4px">
            <el-text>最近练习：{{ formatTime(recent.last_practice_at) }}</el-text>
            <el-text>最近小测：{{ formatTime(recent.last_quiz_at) }}</el-text>
            <el-text>最近视频：{{ formatTime(recent.last_video_at) }}</el-text>
            <el-text>最近表情：{{ formatTime(recent.last_expression_at) }}</el-text>
          </div>
        </el-card>
      </div>

      <div style="margin-top: 12px; display: grid; gap: 12px; grid-template-columns: minmax(260px, 1fr) minmax(260px, 1fr);">
        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">薄弱知识点 Top5</div>
          <el-empty v-if="weakPoints.length === 0" description="暂无数据" />
          <div v-else style="display: grid; gap: 8px">
            <div v-for="kp in weakPoints" :key="kp.kp_id" style="display: flex; align-items: center; justify-content: space-between">
              <div>{{ kp.code }} {{ kp.title }}</div>
              <el-tag size="small" type="warning">{{ Math.round((kp.mastery || 0) * 100) }}%</el-tag>
            </div>
          </div>
        </el-card>
        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">掌握度热力</div>
          <el-empty v-if="!hasKps" description="暂无知识点" />
          <div
            v-else
            style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px"
          >
            <div
              v-for="kp in masteryMap"
              :key="kp.kp_id"
              style="border-radius: 12px; padding: 10px; color: var(--app-ink); border: 1px solid rgba(255,255,255,0.08)"
              :style="{ background: `linear-gradient(135deg, ${masteryColor(kp.mastery)}18, ${masteryColor(kp.mastery)}55)` }"
            >
              <div style="font-weight: 600; font-size: 13px">{{ kp.code }}</div>
              <div style="font-size: 12px; color: var(--app-ink-soft)">{{ kp.title }}</div>
              <div style="margin-top: 6px; font-weight: 700">{{ Math.round((kp.mastery || 0) * 100) }}%</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </el-card>
</template>
