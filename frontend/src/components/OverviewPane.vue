<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";

const props = defineProps<{ subject: string; grade: string }>();

type Summary = {
  total_kps: number;
  mastered: number;
  in_progress: number;
  not_mastered: number;
  avg_mastery: number;
  dynamic_score?: number;
  risk_level?: string;
};
type MasteryItem = { kp_id: number; code: string; title: string; mastery: number; status?: string; chapter?: string };
type Recent = {
  last_practice_at?: string | null;
  last_quiz_at?: string | null;
  last_video_at?: string | null;
};
type Practice7d = { total: number; correct: number; accuracy: number };
type StageInfo = {
  stage_id: number;
  stage_title: string;
  stage_order: number;
  dynamic_score: number;
  course_mastery: number;
  trend_label: string;
  risk_level: string;
  reason_summary: string;
};
type Profile = {
  persona_label?: string;
  dynamic_score?: number;
  risk_level?: string;
  course_mastery?: number;
  reason_summary?: string;
  dimension_config?: Array<{ key: string; label: string; enabled: boolean; weight: number }>;
  dynamic_breakdown?: Record<string, number | string> | null;
  portrait_timeline?: Array<{
    updated_at: string;
    persona_label: string;
    dynamic_score: number;
    course_mastery: number;
    risk_level: string;
    stage_title?: string | null;
    trend_label?: string | null;
    reason_summary?: string;
  }>;
  current_stage?: StageInfo | null;
  stage_history?: StageInfo[];
};

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
const profile = ref<Profile | null>(null);
const analysisWindowDays = ref(7);

const avgPercent = computed(() => Math.round((summary.value.avg_mastery || 0) * 100));
const hasKps = computed(() => masteryMap.value.length > 0);
const currentStage = computed(() => profile.value?.current_stage ?? null);
const stageHistory = computed(() => profile.value?.stage_history ?? []);
const portraitTimeline = computed(() => profile.value?.portrait_timeline ?? []);
const breakdown = computed(() => profile.value?.dynamic_breakdown ?? null);
const dimensionWeights = computed(() => (profile.value?.dimension_config ?? []).filter((item) => item.enabled));
const stageComparison = computed(() => {
  const current = stageHistory.value.length ? stageHistory.value[stageHistory.value.length - 1] : currentStage.value ?? null;
  const previous = stageHistory.value.length > 1 ? stageHistory.value[stageHistory.value.length - 2] : null;
  if (!current) return null;
  return {
    current,
    previous,
    deltaScore: previous ? current.dynamic_score - previous.dynamic_score : 0,
    deltaMastery: previous ? current.course_mastery - previous.course_mastery : 0,
  };
});
const breakdownItems = computed(() => {
  if (!breakdown.value) return [];
  const entries: Array<{ key: string; label: string; value: number; hint: string }> = [
    { key: "learning_frequency", label: "学习频次", value: Number(breakdown.value.learning_frequency ?? 0), hint: "近30天活跃度" },
    { key: "study_duration", label: "学习时长", value: Number(breakdown.value.study_duration ?? 0), hint: "视频与练习投入" },
    { key: "practice_accuracy", label: "练习正确率", value: Number(breakdown.value.practice_accuracy ?? 0), hint: "练习答对比例" },
    { key: "quiz_accuracy", label: "小测正确率", value: Number(breakdown.value.quiz_accuracy ?? 0), hint: "小测结果表现" },
    { key: "course_mastery", label: "课程掌握度", value: Number(profile.value?.course_mastery ?? 0), hint: "知识点整体掌握" },
    { key: "dynamic_score", label: "动态评分", value: Number(profile.value?.dynamic_score ?? 0), hint: "综合评价结果" },
  ];
  return entries;
});

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
      `/eval/overview?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&days=${analysisWindowDays.value}`
    );
    summary.value = res.data.summary ?? summary.value;
    masteryMap.value = res.data.mastery_map ?? [];
    weakPoints.value = res.data.weak_points ?? [];
    recent.value = res.data.recent_activity ?? {};
    practice7d.value = res.data.practice_7d ?? practice7d.value;
    reviewDue.value = Number(res.data.review_due ?? 0);
    profile.value = res.data.profile ?? null;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载总览失败");
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.subject, props.grade, analysisWindowDays.value],
  () => load(),
  { immediate: true }
);
</script>

<template>
  <el-card class="panel-card">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap">
        <div>
          <div style="font-weight: 700">学习总览</div>
          <div style="font-size: 12px; color: #7b8da6">查看画像、阶段变化和动态评价拆解</div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
          <el-radio-group v-model="analysisWindowDays" size="small">
            <el-radio-button :label="7">近 7 天</el-radio-button>
            <el-radio-button :label="30">近 30 天</el-radio-button>
          </el-radio-group>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
        </div>
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
          <div style="font-size: 12px; color: #6b7d72">当前画像</div>
          <div style="font-weight: 700; font-size: 20px">{{ profile?.persona_label ?? "未生成" }}</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">平均掌握度</div>
          <div style="font-weight: 700; font-size: 22px">{{ avgPercent }}%</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">动态评分</div>
          <div style="font-weight: 700; font-size: 22px">{{ Math.round((summary.dynamic_score || 0) * 100) }}%</div>
        </el-card>
        <el-card shadow="never">
          <div style="font-size: 12px; color: #6b7d72">待复习任务</div>
          <div style="font-weight: 700; font-size: 22px">{{ reviewDue }}</div>
        </el-card>
      </div>

      <div v-if="profile?.reason_summary" class="overview-tip-inline" style="margin-top: 12px">
        <span>当前判断依据</span>
        <HoverTip :content="profile.reason_summary" />
      </div>

      <div v-if="currentStage" style="margin-top: 12px; display: grid; gap: 12px; grid-template-columns: minmax(320px, 1.1fr) minmax(260px, 0.9fr);">
        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">当前阶段概览</div>
          <div style="display: grid; gap: 8px;">
            <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
              <div>
                <div style="font-size: 12px; color: #5b7797;">阶段 {{ currentStage.stage_order }}</div>
                <div style="font-size: 18px; font-weight: 700; color: var(--app-ink);">{{ currentStage.stage_title }}</div>
              </div>
              <el-tag :type="currentStage.trend_label === '进步' ? 'success' : currentStage.trend_label === '退步' ? 'danger' : 'info'">
                {{ currentStage.trend_label }}
              </el-tag>
            </div>
            <div style="display:grid; gap:8px; grid-template-columns: repeat(3, minmax(0, 1fr));">
              <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
                <div style="font-size:12px; color:#5b7797;">阶段评分</div>
                <div style="font-size:20px; font-weight:800;">{{ Math.round((currentStage.dynamic_score || 0) * 100) }}%</div>
              </div>
              <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
                <div style="font-size:12px; color:#5b7797;">阶段掌握度</div>
                <div style="font-size:20px; font-weight:800;">{{ Math.round((currentStage.course_mastery || 0) * 100) }}%</div>
              </div>
              <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
                <div style="font-size:12px; color:#5b7797;">阶段等级</div>
                <div style="font-size:20px; font-weight:800;">{{ currentStage.risk_level }}</div>
              </div>
            </div>
            <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef; color: var(--app-ink); line-height: 1.7;">
              {{ currentStage.reason_summary }}
            </div>
          </div>
        </el-card>

        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">阶段趋势</div>
          <el-empty v-if="stageHistory.length === 0" description="暂无阶段数据" />
          <div v-else style="display:grid; gap:8px;">
            <div v-for="item in stageHistory" :key="item.stage_id" style="display:flex; align-items:center; justify-content:space-between; gap:10px; padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
              <div>
                <div style="font-size:12px; color:#5b7797;">阶段 {{ item.stage_order }}</div>
                <div style="font-weight:700; color:var(--app-ink);">{{ item.stage_title }}</div>
              </div>
              <div style="display:grid; justify-items:end; gap:4px;">
                <el-tag size="small" :type="item.trend_label === '进步' ? 'success' : item.trend_label === '退步' ? 'danger' : 'info'">{{ item.trend_label }}</el-tag>
                <span style="font-size:12px; color:#5b7797;">{{ Math.round((item.dynamic_score || 0) * 100) }}%</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <div style="margin-top: 12px; display: grid; gap: 12px; grid-template-columns: minmax(300px, 0.95fr) minmax(300px, 1.05fr);">
        <el-card shadow="never">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom: 8px;">
            <div style="font-weight: 600">评价权重可视化</div>
            <el-tag size="small" effect="plain">阶段维度权重</el-tag>
          </div>
          <el-empty v-if="dimensionWeights.length === 0" description="暂无权重配置" />
          <div v-else style="display:grid; gap:10px;">
            <div v-for="item in dimensionWeights" :key="item.key" style="display:grid; gap:6px;">
              <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
                <span style="color:#455b75; font-size:13px;">{{ item.label }}</span>
                <strong style="color:var(--app-ink);">{{ Math.round((item.weight || 0) * 100) }}%</strong>
              </div>
              <el-progress :percentage="Math.round((item.weight || 0) * 100)" :stroke-width="10" />
            </div>
          </div>
        </el-card>

        <el-card shadow="never">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom: 8px;">
            <div style="font-weight: 600">阶段趋势对比</div>
            <el-tag size="small" effect="plain">{{ analysisWindowDays }} 天窗口</el-tag>
          </div>
          <el-empty v-if="!stageComparison" description="暂无阶段对比" />
          <div v-else style="display:grid; gap:10px;">
            <div style="display:grid; gap:8px; grid-template-columns: repeat(3, minmax(0, 1fr));">
              <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
                <div style="font-size:12px; color:#5b7797;">当前评分</div>
                <div style="font-size:20px; font-weight:800;">{{ Math.round((stageComparison.current.dynamic_score || 0) * 100) }}%</div>
              </div>
              <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
                <div style="font-size:12px; color:#5b7797;">上次评分</div>
                <div style="font-size:20px; font-weight:800;">{{ stageComparison.previous ? Math.round((stageComparison.previous.dynamic_score || 0) * 100) : "—" }}%</div>
              </div>
              <div style="padding: 10px 12px; border-radius: 14px; background:#f7fafc; border:1px solid #e1e8ef;">
                <div style="font-size:12px; color:#5b7797;">变化趋势</div>
                <div style="font-size:20px; font-weight:800;">
                  {{ stageComparison.deltaScore >= 0 ? "+" : "" }}{{ Math.round(stageComparison.deltaScore * 100) }}%
                </div>
              </div>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:8px; font-size:13px; color:#47607e; line-height:1.7;">
              <span>当前阶段：{{ stageComparison.current.stage_title }}</span>
              <span v-if="stageComparison.previous">上一阶段：{{ stageComparison.previous.stage_title }}</span>
              <span>掌握度变化：{{ stageComparison.deltaMastery >= 0 ? "+" : "" }}{{ Math.round(stageComparison.deltaMastery * 100) }}%</span>
            </div>
            <div style="padding: 12px; border-radius: 14px; border: 1px solid #e1e8ef; background:#f8fbff; color:#41566f; line-height:1.7;">
              通过最近阶段的评分变化，系统会判断当前画像是否稳定，并决定下一步推荐是否更保守或更激进。
            </div>
          </div>
        </el-card>
      </div>

      <div style="margin-top: 12px; display: grid; gap: 12px; grid-template-columns: minmax(300px, 1fr) minmax(320px, 1fr);">
        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">学习者画像时间轴</div>
          <el-empty v-if="portraitTimeline.length === 0" description="暂无画像时间轴" />
          <div v-else style="display: grid; gap: 8px;">
            <div
              v-for="item in portraitTimeline"
              :key="`${item.updated_at}-${item.stage_title || item.persona_label}`"
              style="padding: 12px; border-radius: 14px; border: 1px solid #e1e8ef; background: #f8fbff; display: grid; gap: 6px;"
            >
              <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
                <strong style="color: var(--app-ink);">{{ item.stage_title || item.persona_label }}</strong>
                <el-tag size="small" :type="item.trend_label === '进步' ? 'success' : item.trend_label === '退步' ? 'danger' : 'info'">
                  {{ item.trend_label || "持平" }}
                </el-tag>
              </div>
              <div style="display:flex; flex-wrap:wrap; gap:8px; font-size:12px; color:#647a94;">
                <span>{{ new Date(item.updated_at).toLocaleString() }}</span>
                <span>画像：{{ item.persona_label }}</span>
                <span>评分：{{ Math.round((item.dynamic_score || 0) * 100) }}%</span>
                <span>掌握度：{{ Math.round((item.course_mastery || 0) * 100) }}%</span>
                <span>风险：{{ item.risk_level }}</span>
              </div>
              <div style="font-size:13px; color:#41566f; line-height:1.7;">
                {{ item.reason_summary || "系统根据阶段记录生成该画像。" }}
              </div>
            </div>
          </div>
        </el-card>

        <el-card shadow="never">
          <div style="font-weight: 600; margin-bottom: 8px">动态评价拆解</div>
          <div v-if="!breakdown" style="color:#8ea1ba; font-size:13px;">暂无拆解信息</div>
          <div v-else style="display:grid; gap:10px;">
            <div v-for="item in breakdownItems" :key="item.key" style="display:grid; gap:6px;">
              <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
                <span style="color:#455b75; font-size:13px;">{{ item.label }}</span>
                <strong style="color:var(--app-ink);">{{ Math.round((item.value || 0) * 100) }}%</strong>
              </div>
              <el-progress :percentage="Math.round((item.value || 0) * 100)" :stroke-width="10" />
              <div style="font-size:12px; color:#8b9bb1;">{{ item.hint }}</div>
            </div>
            <div style="padding: 12px; border-radius: 14px; border: 1px solid #e1e8ef; background:#f8fbff; color:#41566f; line-height:1.7;">
              {{ breakdown.summary || profile?.reason_summary || "系统会综合行为、作答和掌握度生成动态评价。" }}
            </div>
          </div>
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
            <el-text>最近视频：{{ formatTime(recent.last_video_at) }}</el-text>
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

<style scoped>
.overview-tip-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #637995;
  font-size: 13px;
  font-weight: 700;
}
</style>
