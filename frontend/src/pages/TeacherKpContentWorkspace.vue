<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import type { Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Reading, EditPen, Collection, FolderOpened, Share, Upload, ArrowDown, Setting, Connection, CircleCheck } from "@element-plus/icons-vue";
import { api } from "../api";

type KpInfo = {
  id: number;
  code: string;
  title: string;
  chapter?: string;
  description?: string;
  knowledge_tag?: string;
  ability_tag?: string;
  literacy_tag?: string;
  importance?: number;
  difficulty?: number;
};

type ResourceItem = {
  id: number;
  kp_id: number;
  type: string;
  title: string;
  url: string;
  category?: string;
  description?: string;
  tags?: string;
  original_file_name?: string;
  file_extension?: string;
  detected_mime_type?: string;
  detected_resource_type?: string;
  preview_type?: string;
  preview_status?: string;
  preview_error?: string;
  converted_preview_url?: string;
  original_file_url?: string;
  file_size_bytes?: number;
  extension_mismatch?: boolean;
  source_kind?: string;
};

type DetectedUpload = {
  original_file_name: string;
  file_extension: string;
  detected_mime_type: string;
  detected_resource_type: string;
  preview_type: string;
  preview_label: string;
  extension_mismatch: boolean;
  upload_rule?: { max_size_bytes?: number; label?: string };
};

type ClientUploadMeta = {
  kind: "video" | "image" | "other";
  width?: number;
  height?: number;
  duration?: number;
  warnings: string[];
};

type QuestionRow = {
  id: number;
  kp_id: number;
  type: string;
  prompt: string;
  options: string[];
  answer: string;
  explanation: string;
  difficulty: number;
  cognitive_level?: string;
  ability_subtags?: string;
};

type AssignedPracticeRow = {
  id: number;
  kp_id: number;
  question_id: number;
  order: number;
  type: string;
  prompt: string;
};

type EdgeRow = {
  id: number;
  prereq_id: number;
  next_id: number;
  relation_type: string;
};

type RelationDirection = "incoming" | "outgoing";
type RelationTypeValue = "prerequisite" | "related" | "support" | "contains";
type SectionKey = "basic" | "learning" | "practice" | "relation" | "check";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const relationSaving = ref(false);
const activeSection = ref<SectionKey>("basic");

const kp = ref<KpInfo | null>(null);
const resources = ref<ResourceItem[]>([]);
const questions = ref<QuestionRow[]>([]);
const assignedPractice = ref<AssignedPracticeRow[]>([]);
const graphKps = ref<KpInfo[]>([]);
const graphEdges = ref<EdgeRow[]>([]);

const resourceDialogOpen = ref(false);
const resourceEditingId = ref<number | null>(null);
const resourceDialogMode = ref<"learning" | "recommend">("learning");
const resourceDragActive = ref(false);
const resourceForm = reactive({
  title: "",
  url: "",
  category: "learning",
  tags: "",
  description: "",
  source_kind: "upload",
});
const resourceUploadFile = ref<File | null>(null);
const detectedUpload = ref<DetectedUpload | null>(null);
const clientUploadMeta = ref<ClientUploadMeta | null>(null);

const questionDialogOpen = ref(false);
const questionEditingId = ref<number | null>(null);
const relationForm = reactive<{
  targetId: number | null;
  relationType: RelationTypeValue;
  direction: RelationDirection;
}>({
  targetId: null,
  relationType: "prerequisite",
  direction: "outgoing",
});

const COGNITIVE_OPTIONS = [
  { value: "remember", label: "记忆 remember" },
  { value: "understand", label: "理解 understand" },
  { value: "apply", label: "应用 apply（高阶）" },
  { value: "analyze", label: "分析 analyze（高阶）" },
  { value: "evaluate", label: "评价 evaluate（高阶）" },
  { value: "create", label: "创造 create（高阶）" },
] as const;

const questionForm = reactive({
  type: "mcq",
  prompt: "",
  options_text: "",
  answer: "",
  explanation: "",
  difficulty: 0.5,
  cognitive_level: "understand",
  ability_subtags: "",
});

const kpId = computed(() => {
  const raw = Number(route.params.kpId);
  return Number.isFinite(raw) && raw > 0 ? raw : 0;
});

const subject = computed(() => String(route.query.subject || ""));
const grade = computed(() => String(route.query.grade || "通用"));
const mode = computed(() => String(route.query.mode || ""));
const createMode = computed(() => kpId.value === 0 || mode.value === "create");

const learningResources = computed(() =>
  resources.value.filter((item) => (item.category || "learning") !== "recommend")
);

const recommendResources = computed(() =>
  resources.value.filter((item) => (item.category || "learning") === "recommend")
);
const groupedLearningResources = computed(() => groupResources(learningResources.value));
const groupedRecommendResources = computed(() => groupResources(recommendResources.value));
const teacherResourceView = ref<"all" | "grouped">("all");
const allLearningResourcesSorted = computed(() =>
  [...learningResources.value].sort((a, b) => a.title.localeCompare(b.title, "zh-Hans-CN")),
);
const resourceTagPreview = computed(() =>
  resourceForm.tags
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 6)
);
const resourceDescriptionCount = computed(() => resourceForm.description.trim().length);
const currentKpLabel = computed(() => {
  if (createMode.value) return "新建知识点";
  if (!kp.value) return "当前知识点";
  return `${kp.value.code} ${kp.value.title}`;
});

const kpForm = reactive({
  code: "",
  title: "",
  chapter: "",
  description: "",
  knowledge_tag: "",
  ability_tag: "",
  literacy_tag: "",
  importance: 0.5,
  difficulty: 0.5,
});

function resetKpForm(chapter = "") {
  Object.assign(kpForm, {
    code: "",
    title: "",
    chapter,
    description: "",
    knowledge_tag: "",
    ability_tag: "",
    literacy_tag: "",
    importance: 0.5,
    difficulty: 0.5,
  });
}

function syncKpFormFromNode(node: Partial<KpInfo> | null | undefined) {
  Object.assign(kpForm, {
    code: node?.code || "",
    title: node?.title || "",
    chapter: node?.chapter || String(route.query.chapter || ""),
    description: node?.description || "",
    knowledge_tag: node?.knowledge_tag || "",
    ability_tag: node?.ability_tag || "",
    literacy_tag: node?.literacy_tag || "",
    importance: node?.importance ?? 0.5,
    difficulty: node?.difficulty ?? 0.5,
  });
}

const assignedQuestionIds = computed(() => new Set(assignedPractice.value.map((item) => item.question_id)));
const kpMap = computed(() => new Map(graphKps.value.map((item) => [item.id, item])));

const stats = computed(() => ({
  basic: createMode.value ? 0 : 1,
  learning: learningResources.value.length,
  practice: assignedPractice.value.length,
  relation: kp.value ? graphEdges.value.filter((item) => item.prereq_id === kp.value?.id || item.next_id === kp.value?.id).length : 0,
  check: completenessScore.value,
}));

const sectionCards = computed(() => {
  const icons: Record<SectionKey, Component> = {
    basic: Setting,
    learning: Reading,
    practice: EditPen,
    relation: Connection,
    check: CircleCheck,
  };
  return [
    {
      key: "basic" as SectionKey,
      title: "基础信息",
      desc: "名称、标签、难度与章节",
      count: createMode.value ? "新建" : "已建",
      icon: icons.basic,
    },
    {
      key: "learning" as SectionKey,
      title: "学习资料",
      desc: "视频、文档、课件与外链",
      count: stats.value.learning,
      icon: icons.learning,
    },
    {
      key: "practice" as SectionKey,
      title: "练习与题库",
      desc: "题目与随堂练习顺序",
      count: stats.value.practice,
      icon: icons.practice,
    },
    {
      key: "relation" as SectionKey,
      title: "图谱关系",
      desc: "前置、后继、关联与支撑",
      count: stats.value.relation,
      icon: icons.relation,
    },
    {
      key: "check" as SectionKey,
      title: "配置检查",
      desc: "检查是否已形成学习闭环",
      count: `${stats.value.check}%`,
      icon: icons.check,
    },
  ];
});

const graphLinkQuery = computed(() => ({
  subject: subject.value || undefined,
  grade: grade.value || undefined,
}));

const resourceDialogTitle = computed(() => {
  const isRec = resourceDialogMode.value === "recommend";
  if (resourceEditingId.value) {
    return isRec ? "编辑推荐资源" : "编辑学习资源";
  }
  return isRec ? "新增推荐资源" : "新增学习资源";
});

const relationOptions = computed(() =>
  graphKps.value
    .filter((item) => item.id !== kpId.value)
    .sort((a, b) => `${a.chapter || ""}${a.code}${a.title}`.localeCompare(`${b.chapter || ""}${b.code}${b.title}`, "zh-Hans-CN"))
    .map((item) => ({
      value: item.id,
      label: `${item.code} ${item.title}${item.chapter ? ` · ${item.chapter}` : ""}`,
    })),
);

const relationSummary = computed(() => {
  const currentId = kpId.value;
  const findNode = (id: number) => kpMap.value.get(id);
  const rows = graphEdges.value.filter((item) => item.prereq_id === currentId || item.next_id === currentId);
  return {
    prerequisitesIn: rows
      .filter((item) => item.relation_type === "prerequisite" && item.next_id === currentId)
      .map((item) => ({ edgeId: item.id, node: findNode(item.prereq_id), text: "作为当前知识点的前置知识" }))
      .filter((item) => item.node),
    prerequisitesOut: rows
      .filter((item) => item.relation_type === "prerequisite" && item.prereq_id === currentId)
      .map((item) => ({ edgeId: item.id, node: findNode(item.next_id), text: "作为当前知识点的后继知识" }))
      .filter((item) => item.node),
    related: rows
      .filter((item) => item.relation_type === "related")
      .map((item) => {
        const targetId = item.prereq_id === currentId ? item.next_id : item.prereq_id;
        return { edgeId: item.id, node: findNode(targetId), text: "关联知识点" };
      })
      .filter((item) => item.node),
    support: rows
      .filter((item) => item.relation_type === "support")
      .map((item) => ({
        edgeId: item.id,
        node: findNode(item.prereq_id === currentId ? item.next_id : item.prereq_id),
        text: item.prereq_id === currentId ? "由当前知识点支撑" : "支撑当前知识点",
      }))
      .filter((item) => item.node),
    contains: rows
      .filter((item) => item.relation_type === "contains")
      .map((item) => ({
        edgeId: item.id,
        node: findNode(item.prereq_id === currentId ? item.next_id : item.prereq_id),
        text: item.prereq_id === currentId ? "当前知识点包含" : "包含当前知识点",
      }))
      .filter((item) => item.node),
  };
});

const checklistItems = computed(() => {
  const relationTotal =
    relationSummary.value.prerequisitesIn.length +
    relationSummary.value.prerequisitesOut.length +
    relationSummary.value.related.length +
    relationSummary.value.support.length +
    relationSummary.value.contains.length;
  return [
    { key: "code", label: "已填写知识点编码", done: Boolean(kpForm.code.trim()), detail: kpForm.code.trim() || "缺少编码" },
    { key: "title", label: "已填写知识点名称", done: Boolean(kpForm.title.trim()), detail: kpForm.title.trim() || "缺少名称" },
    { key: "chapter", label: "已选择所属分类", done: Boolean(kpForm.chapter.trim()), detail: kpForm.chapter.trim() || "缺少分类" },
    { key: "description", label: "已填写知识点描述", done: Boolean(kpForm.description.trim()), detail: kpForm.description.trim() || "建议补充学习说明" },
    { key: "learning", label: "已配置学习资源", done: learningResources.value.length > 0, detail: `${learningResources.value.length} 个` },
    { key: "practice", label: "已配置练习题", done: questions.value.length > 0, detail: `${questions.value.length} 题` },
    { key: "practiceAssigned", label: "已加入随堂练习", done: assignedPractice.value.length > 0, detail: `${assignedPractice.value.length} 题` },
    { key: "relation", label: "已配置图谱关系", done: relationTotal > 0, detail: `${relationTotal} 条` },
    { key: "ability", label: "已配置能力标签", done: Boolean(kpForm.ability_tag.trim()), detail: kpForm.ability_tag.trim() || "缺少能力标签" },
    { key: "literacy", label: "已配置素养标签", done: Boolean(kpForm.literacy_tag.trim()), detail: kpForm.literacy_tag.trim() || "缺少素养标签" },
    { key: "recommend", label: "已配置推荐拓展", done: recommendResources.value.length > 0, detail: `${recommendResources.value.length} 个` },
  ];
});

const completenessScore = computed(() => {
  const total = checklistItems.value.length;
  if (!total) return 0;
  const done = checklistItems.value.filter((item) => item.done).length;
  return Math.round((done / total) * 100);
});

const missingChecklistItems = computed(() => checklistItems.value.filter((item) => !item.done));

function parseOptions(text: string) {
  return text
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function resourceTypeLabel(type: string) {
  const map: Record<string, string> = {
    video: "视频",
    pdf: "PDF 文档",
    note: "文档",
    doc: "资料",
    docx: "Word 文档",
    ppt: "课件",
    pptx: "PPT 演示文稿",
    image: "图片",
    link: "外部链接",
    example: "案例",
    book: "推荐书籍",
    recommend_book: "推荐书籍",
  };
  return map[type] || type;
}

function previewStatusLabel(status?: string) {
  const map: Record<string, string> = {
    processing: "处理中",
    ready: "可预览",
    failed: "转换失败",
  };
  return map[status || "ready"] || "可预览";
}

function previewLabel(item: { preview_type?: string }) {
  const map: Record<string, string> = {
    pdf_inline: "PDF 在线预览",
    pdf_after_convert: "转 PDF 预览",
    video_inline: "页面内视频播放",
    image_inline: "页面内图片预览",
    external_link: "新窗口打开",
    download: "下载查看",
  };
  return map[item.preview_type || "download"] || "下载查看";
}

function resourceGroupKey(item: ResourceItem) {
  const type = String(item.detected_resource_type || item.type || "").toLowerCase();
  const previewType = String(item.preview_type || "").toLowerCase();
  if (type === "video" || previewType === "video_inline") return "video";
  if (type === "image" || previewType === "image_inline") return "image";
  if (type === "link" || previewType === "external_link") return "link";
  if (["pdf", "ppt", "pptx", "doc", "docx", "note"].includes(type) || previewType.includes("pdf")) return "document";
  return "other";
}

function resourceGroupTitle(key: string) {
  const map: Record<string, string> = {
    video: "视频资源",
    document: "文档 / 课件",
    image: "图片资源",
    link: "外部链接",
    other: "其他资源",
  };
  return map[key] || "资源";
}

function groupResources(items: ResourceItem[]) {
  const order = ["video", "document", "image", "link", "other"];
  return order
    .map((key) => ({
      key,
      title: resourceGroupTitle(key),
      items: items.filter((item) => resourceGroupKey(item) === key),
    }))
    .filter((group) => group.items.length > 0);
}

function questionTypeLabel(type: string) {
  return type === "blank" ? "填空题" : "选择题";
}

function cognitiveLabel(code?: string) {
  const row = COGNITIVE_OPTIONS.find((item) => item.value === (code || "").toLowerCase());
  return row?.label ?? (code || "—");
}

async function loadData() {
  loading.value = true;
  try {
    if (createMode.value) {
      kp.value = null;
      resources.value = [];
      questions.value = [];
      assignedPractice.value = [];
      graphEdges.value = [];
      if (subject.value) {
        const kpsRes = await api.get(`/graph/kps?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
        graphKps.value = Array.isArray(kpsRes.data) ? kpsRes.data : [];
      } else {
        graphKps.value = [];
      }
      resetKpForm(String(route.query.chapter || ""));
      activeSection.value = "basic";
      return;
    }
    if (!kpId.value) {
      ElMessage.warning("缺少知识点参数");
      goBack();
      return;
    }
    const [nodeRes, questionRes, assignedRes, kpsRes, edgesRes] = await Promise.all([
      api.get(`/graph/node/${kpId.value}`),
      api.get(`/admin/questions?kp_id=${kpId.value}&page=1&page_size=200`),
      api.get(`/admin/kp-questions?kp_id=${kpId.value}`),
      api.get(`/graph/kps?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`),
      api.get(`/admin/edges?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}&page=1&page_size=500`),
    ]);

    const node = nodeRes.data?.kp;
    kp.value = node
      ? {
          id: node.id,
          code: node.code,
          title: node.title,
          chapter: node.chapter,
          description: node.description,
          knowledge_tag: node.knowledge_tag,
          ability_tag: node.ability_tag,
          literacy_tag: node.literacy_tag,
          importance: node.importance,
          difficulty: node.difficulty,
        }
      : null;
    syncKpFormFromNode(kp.value);

    resources.value = nodeRes.data?.resource_list ?? [];
    questions.value = questionRes.data?.items ?? [];
    assignedPractice.value = assignedRes.data ?? [];
    graphKps.value = Array.isArray(kpsRes.data) ? kpsRes.data : [];
    graphEdges.value = edgesRes.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点内容失败");
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push({
    path: "/teacher/content",
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
    },
  });
}

function openStudentPreview() {
  if (!kpId.value) {
    ElMessage.warning("请先保存知识点，再打开学生预览");
    return;
  }
  const target = router.resolve({
    path: `/teacher/kp-preview/${kpId.value}`,
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      preview: "1",
    },
  });
  window.open(target.href, "_blank", "noopener,noreferrer");
}

async function saveAndBack() {
  const ok = await saveKpMeta();
  if (ok) goBack();
}

function openResourceCreate(mode: "learning" | "recommend") {
  resourceDialogMode.value = mode;
  resourceEditingId.value = null;
  resourceForm.title = "";
  resourceForm.url = "";
  resourceForm.tags = "";
  resourceForm.description = "";
  resourceForm.category = mode === "recommend" ? "recommend" : "learning";
  resourceForm.source_kind = "upload";
  resourceUploadFile.value = null;
  detectedUpload.value = null;
  clientUploadMeta.value = null;
  resourceDialogOpen.value = true;
}

function openResourceEdit(item: ResourceItem, mode: "learning" | "recommend") {
  resourceDialogMode.value = mode;
  resourceEditingId.value = item.id;
  resourceForm.title = item.title;
  resourceForm.url = item.original_file_url || item.url;
  resourceForm.tags = item.tags || "";
  resourceForm.description = item.description || "";
  resourceForm.category = item.category || (mode === "recommend" ? "recommend" : "learning");
  resourceForm.source_kind = item.source_kind || "external";
  resourceUploadFile.value = null;
  clientUploadMeta.value = null;
  detectedUpload.value = item.original_file_name
    ? {
        original_file_name: item.original_file_name || "",
        file_extension: item.file_extension || "",
        detected_mime_type: item.detected_mime_type || "",
        detected_resource_type: item.detected_resource_type || item.type,
        preview_type: item.preview_type || "download",
        preview_label: previewLabel(item),
        extension_mismatch: Boolean(item.extension_mismatch),
      }
    : null;
  resourceDialogOpen.value = true;
}

async function inspectUpload(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post("/admin/kp-resources/detect", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  detectedUpload.value = res.data;
}

async function inspectBrowserMeta(file: File, detectedType?: string) {
  const normalized = String(detectedType || "").toLowerCase();
  const objectUrl = URL.createObjectURL(file);
  try {
    if (normalized === "video") {
      const meta = await new Promise<ClientUploadMeta>((resolve, reject) => {
        const video = document.createElement("video");
        video.preload = "metadata";
        video.onloadedmetadata = () => {
          const warnings: string[] = [];
          const width = Number(video.videoWidth || 0);
          const height = Number(video.videoHeight || 0);
          const duration = Number(video.duration || 0);
          if (width > 0 && height > 0) {
            const ratio = width / height;
            if (ratio < 1.3) warnings.push("建议使用 16:9 左右的横屏视频，当前比例偏窄。");
            if (width < 960 || height < 540) warnings.push("当前分辨率偏低，学生端播放可能不够清晰。");
          }
          if (duration > 1800) warnings.push("单个视频超过 30 分钟，建议拆分成多个短视频。");
          resolve({ kind: "video", width, height, duration, warnings });
        };
        video.onerror = () => reject(new Error("读取视频元数据失败"));
        video.src = objectUrl;
      });
      clientUploadMeta.value = meta;
      return;
    }
    if (normalized === "image") {
      const meta = await new Promise<ClientUploadMeta>((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
          const warnings: string[] = [];
          const width = Number(image.width || 0);
          const height = Number(image.height || 0);
          if (width < 960 || height < 540) warnings.push("当前图片尺寸偏小，投屏或大屏展示时可能不清晰。");
          resolve({ kind: "image", width, height, warnings });
        };
        image.onerror = () => reject(new Error("读取图片尺寸失败"));
        image.src = objectUrl;
      });
      clientUploadMeta.value = meta;
      return;
    }
    clientUploadMeta.value = { kind: "other", warnings: [] };
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

async function setUploadFile(file: File | null) {
  resourceUploadFile.value = file;
  detectedUpload.value = null;
  clientUploadMeta.value = null;
  if (!file) return;
  try {
    await inspectUpload(file);
    await inspectBrowserMeta(file, detectedUpload.value?.detected_resource_type);
    if (!resourceForm.title.trim()) {
      resourceForm.title = file.name.replace(/\.[^.]+$/, "");
    }
  } catch (e: any) {
    resourceUploadFile.value = null;
    ElMessage.error(e?.response?.data?.detail ?? "识别文件类型失败");
  }
}

async function handleUploadChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0] || null;
  await setUploadFile(file);
}

function handleUploadDragEnter() {
  resourceDragActive.value = true;
}

function handleUploadDragLeave(event: DragEvent) {
  const current = event.currentTarget as HTMLElement | null;
  const next = event.relatedTarget as Node | null;
  if (current && next && current.contains(next)) return;
  resourceDragActive.value = false;
}

async function handleUploadDrop(event: DragEvent) {
  resourceDragActive.value = false;
  const file = event.dataTransfer?.files?.[0] || null;
  await setUploadFile(file);
}

async function saveResource() {
  if (!kpId.value) return;
  saving.value = true;
  try {
    const trimmedTitle = resourceForm.title.trim();
    const trimmedUrl = resourceForm.url.trim();
    const trimmedTags = resourceForm.tags.trim();
    const trimmedDescription = resourceForm.description.trim();
    if (resourceEditingId.value) {
      if (!trimmedTitle) {
        ElMessage.warning("请输入资源名称");
        saving.value = false;
        return;
      }
      if (resourceForm.source_kind === "external" && !trimmedUrl) {
        ElMessage.warning("请输入外部资源链接");
        saving.value = false;
        return;
      }
      const payload = {
        title: trimmedTitle,
        url: resourceForm.source_kind === "external" ? trimmedUrl : undefined,
        category: resourceForm.category,
        tags: trimmedTags,
        description: trimmedDescription,
      };
      await api.put(`/admin/kp-resources/${resourceEditingId.value}`, payload);
      ElMessage.success("资源已更新");
    } else if (resourceForm.source_kind === "upload") {
      if (!trimmedTitle) {
        ElMessage.warning("请输入资源名称");
        saving.value = false;
        return;
      }
      if (!resourceUploadFile.value || !detectedUpload.value) {
        ElMessage.warning("请先选择文件，系统识别成功后再保存");
        saving.value = false;
        return;
      }
      if (clientUploadMeta.value?.warnings?.length && clientUploadMeta.value.kind === "video") {
        const hardIssue = clientUploadMeta.value.warnings.find((item) => item.includes("偏窄"));
        if (hardIssue) {
          ElMessage.warning("当前视频更适合先调整为横屏教学视频后再上传");
          saving.value = false;
          return;
        }
      }
      const formData = new FormData();
      formData.append("kp_id", String(kpId.value));
      formData.append("title", trimmedTitle);
      formData.append("category", resourceForm.category);
      formData.append("tags", trimmedTags);
      formData.append("description", trimmedDescription);
      formData.append("file", resourceUploadFile.value);
      await api.post("/admin/kp-resources/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      ElMessage.success("资源已上传");
    } else {
      if (!trimmedTitle) {
        ElMessage.warning("请输入资源名称");
        saving.value = false;
        return;
      }
      if (!trimmedUrl) {
        ElMessage.warning("请输入外部资源链接");
        saving.value = false;
        return;
      }
      const payload = {
        kp_id: kpId.value,
        type: "link",
        title: trimmedTitle,
        url: trimmedUrl,
        category: resourceForm.category,
        tags: trimmedTags,
        description: trimmedDescription,
      };
      await api.post("/admin/kp-resources", payload, {
        headers: { "Content-Type": "application/json" },
      });
      ElMessage.success("资源已添加");
    }
    resourceDialogOpen.value = false;
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存资源失败");
  } finally {
    saving.value = false;
  }
}

function handleResourceMoreCommand(cmd: string, item: ResourceItem) {
  if (cmd === "preview") openPreview(item);
  else if (cmd === "original") openOriginal(item);
  else if (cmd === "remove") removeResource(item);
}

function openPreview(item: ResourceItem) {
  window.open(item.converted_preview_url || item.url, "_blank", "noopener,noreferrer");
}

function openOriginal(item: ResourceItem) {
  window.open(item.original_file_url || item.url, "_blank", "noopener,noreferrer");
}

async function removeResource(item: ResourceItem) {
  try {
    await api.delete(`/admin/kp-resources/${item.id}`);
    ElMessage.success("资源已删除");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除资源失败");
  }
}

function openResourceDetail(resourceId: number) {
  router.push({
    path: `/teacher/resources/${resourceId}`,
    query: {
      kp_id: kpId.value ? String(kpId.value) : undefined,
      subject: subject.value || undefined,
      grade: grade.value || undefined,
    },
  });
}

function openQuestionCreate() {
  questionEditingId.value = null;
  questionForm.type = "mcq";
  questionForm.prompt = "";
  questionForm.options_text = "";
  questionForm.answer = "";
  questionForm.explanation = "";
  questionForm.difficulty = 0.5;
  questionForm.cognitive_level = "understand";
  questionForm.ability_subtags = "";
  questionDialogOpen.value = true;
}

function openQuestionEdit(item: QuestionRow) {
  questionEditingId.value = item.id;
  questionForm.type = item.type;
  questionForm.prompt = item.prompt;
  questionForm.options_text = (item.options ?? []).join("\n");
  questionForm.answer = item.answer;
  questionForm.explanation = item.explanation;
  questionForm.difficulty = item.difficulty ?? 0.5;
  questionForm.cognitive_level = item.cognitive_level || "understand";
  questionForm.ability_subtags = item.ability_subtags || "";
  questionDialogOpen.value = true;
}

async function saveQuestion() {
  if (!kpId.value) return;
  saving.value = true;
  const payload = {
    kp_id: kpId.value,
    type: questionForm.type,
    prompt: questionForm.prompt,
    options: questionForm.type === "mcq" ? parseOptions(questionForm.options_text) : [],
    answer: questionForm.answer,
    explanation: questionForm.explanation,
    difficulty: questionForm.difficulty,
    cognitive_level: questionForm.cognitive_level,
    ability_subtags: questionForm.ability_subtags.trim(),
  };
  try {
    if (questionEditingId.value) {
      await api.put(`/admin/questions/${questionEditingId.value}`, payload);
      ElMessage.success("题目已更新");
    } else {
      await api.post("/admin/questions", payload);
      ElMessage.success("题目已添加");
    }
    questionDialogOpen.value = false;
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存题目失败");
  } finally {
    saving.value = false;
  }
}

async function removeQuestion(id: number) {
  try {
    await api.delete(`/admin/questions/${id}`);
    ElMessage.success("题目已删除");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除题目失败");
  }
}

async function assignQuestionToPractice(questionId: number) {
  try {
    await api.post("/admin/kp-questions", {
      kp_id: kpId.value,
      question_ids: [questionId],
    });
    ElMessage.success("已加入练习");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加入练习失败");
  }
}

async function removeAssignedPractice(assignmentId: number) {
  try {
    await api.delete(`/admin/kp-questions/${assignmentId}`);
    ElMessage.success("已移出练习");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "移出练习失败");
  }
}

async function createRelation() {
  if (!kpId.value) {
    ElMessage.warning("请先保存知识点，再配置图谱关系");
    return;
  }
  if (!relationForm.targetId) {
    ElMessage.warning("请选择目标知识点");
    return;
  }
  relationSaving.value = true;
  try {
    let prereqId = kpId.value;
    let nextId = relationForm.targetId;
    if (relationForm.relationType === "prerequisite") {
      if (relationForm.direction === "incoming") {
        prereqId = relationForm.targetId;
        nextId = kpId.value;
      }
    } else if (relationForm.direction === "incoming") {
      prereqId = relationForm.targetId;
      nextId = kpId.value;
    }
    await api.post("/admin/edges", {
      subject: subject.value,
      grade: grade.value,
      prereq_id: prereqId,
      next_id: nextId,
      relation_type: relationForm.relationType,
    });
    ElMessage.success("图谱关系已添加");
    relationForm.targetId = null;
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "添加关系失败");
  } finally {
    relationSaving.value = false;
  }
}

async function removeRelation(edgeId: number) {
  try {
    await api.delete(`/admin/edges/${edgeId}`);
    ElMessage.success("图谱关系已删除");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除关系失败");
  }
}

function jumpToSection(section: SectionKey) {
  activeSection.value = section;
}

async function saveKpMeta() {
  saving.value = true;
  try {
    const payload = {
      subject: subject.value || "",
      grade: grade.value || "通用",
      code: kpForm.code.trim(),
      title: kpForm.title.trim(),
      description: kpForm.description.trim(),
      chapter: kpForm.chapter.trim(),
      knowledge_tag: kpForm.knowledge_tag.trim(),
      ability_tag: kpForm.ability_tag.trim(),
      literacy_tag: kpForm.literacy_tag.trim(),
      importance: kpForm.importance,
      difficulty: kpForm.difficulty,
    };
    if (!payload.code) {
      ElMessage.warning("请输入知识点编码");
      return false;
    }
    if (!payload.title) {
      ElMessage.warning("请输入知识点名称");
      return false;
    }
    if (createMode.value) {
      const res = await api.post("/admin/kps", payload);
      const newId = Number(res.data?.id || 0);
      ElMessage.success("知识点已创建");
      if (newId > 0) {
        router.replace({
          path: `/teacher/kp-content/${newId}`,
          query: {
            subject: subject.value || undefined,
            grade: grade.value || undefined,
            from: "graph-workspace",
          },
        });
      } else {
        await loadData();
      }
      return true;
    }
    if (!kpId.value) {
      ElMessage.warning("缺少知识点参数");
      return false;
    }
    await api.put(`/admin/kps/${kpId.value}`, payload);
    ElMessage.success("基础信息已保存");
    await loadData();
    return true;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存知识点失败");
    return false;
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await loadData();
});

watch(
  () => [route.params.kpId, route.query.mode, route.query.chapter, route.query.subject, route.query.grade],
  () => {
    loadData();
  },
);
</script>

<template>
  <div class="teacher-content-page" v-loading="loading">
    <div class="teacher-content-page__inner">
      <nav class="content-breadcrumb-wrap" aria-label="页面位置">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <router-link class="content-breadcrumb-link" :to="{ path: '/teacher/workspace' }">
              <el-icon class="content-breadcrumb-icon"><FolderOpened /></el-icon>
              我的课程
            </router-link>
          </el-breadcrumb-item>
          <el-breadcrumb-item>
            <router-link class="content-breadcrumb-link" :to="{ path: '/teacher/content', query: graphLinkQuery }">
              <el-icon class="content-breadcrumb-icon"><Share /></el-icon>
              知识图谱
            </router-link>
          </el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentKpLabel }}</el-breadcrumb-item>
        </el-breadcrumb>
      </nav>

      <header class="content-topbar panel-shell">
        <div class="content-topbar__left">
          <button type="button" class="content-back" @click="goBack">
            <span class="content-back__text">返回图谱</span>
          </button>
          <div class="content-topbar__titles">
            <div class="content-eyebrow">知识点配置</div>
            <h1 class="content-title">知识点配置工作台</h1>
            <p class="content-subtitle">围绕当前知识点完成基础信息、学习资源、练习题库、图谱关系和完整度检查。</p>
          </div>
        </div>
        <div class="content-topbar__actions">
          <el-button :loading="saving" @click="saveKpMeta">保存基础信息</el-button>
          <el-button type="primary" :loading="saving" @click="saveAndBack">保存并返回图谱</el-button>
        </div>
      </header>

      <section class="content-meta panel-shell">
        <div class="content-meta__head">
          <div>
            <h3>{{ createMode ? "创建知识点" : "基础信息" }}</h3>
            <p>{{ createMode ? "先完成基础信息保存，保存成功后即可继续配置内容。" : "这里定义知识点的名称、标签、难度和所属分类，是后续资源与题目配置的基础。" }}</p>
          </div>
          <el-button type="primary" :loading="saving" @click="saveKpMeta">
            {{ createMode ? "创建知识点" : "保存基础信息" }}
          </el-button>
        </div>
        <div class="content-meta__grid">
          <el-form-item label="知识点编码"><el-input v-model="kpForm.code" placeholder="例如 OS-04" /></el-form-item>
          <el-form-item label="知识点名称"><el-input v-model="kpForm.title" placeholder="例如 同步与互斥" /></el-form-item>
          <el-form-item label="所属分类"><el-input v-model="kpForm.chapter" placeholder="例如 进程管理" /></el-form-item>
          <el-form-item label="知识目标"><el-input v-model="kpForm.knowledge_tag" placeholder="例如 临界区、信号量" /></el-form-item>
          <el-form-item label="能力标签"><el-input v-model="kpForm.ability_tag" placeholder="例如 逻辑推理,系统分析" /></el-form-item>
          <el-form-item label="素养标签"><el-input v-model="kpForm.literacy_tag" placeholder="例如 主动学习,规范意识" /></el-form-item>
          <el-form-item label="重要度"><el-input-number v-model="kpForm.importance" :min="0" :max="1" :step="0.05" /></el-form-item>
          <el-form-item label="理解难度"><el-input-number v-model="kpForm.difficulty" :min="0" :max="1" :step="0.05" /></el-form-item>
          <el-form-item class="content-meta__full" label="知识点描述">
            <el-input v-model="kpForm.description" type="textarea" :rows="3" placeholder="说明学生学什么、为什么重要、建议如何学习" />
          </el-form-item>
        </div>
      </section>

      <section class="content-summary" aria-label="配置概览">
        <div class="summary-card" v-for="card in sectionCards" :key="card.key">
          <div class="summary-card__icon" :class="`summary-card__icon--${card.key}`" aria-hidden="true">
            <el-icon :size="22"><component :is="card.icon" /></el-icon>
          </div>
          <div class="summary-card__body">
            <span class="summary-card__label">{{ card.title }}</span>
            <strong class="summary-card__value">{{ card.count }}</strong>
            <small class="summary-card__desc">{{ card.desc }}</small>
          </div>
        </div>
      </section>

      <section v-if="createMode" class="content-create-empty panel-shell">
        <strong>基础信息已准备好后，再继续配置内容</strong>
        <span>创建成功后，这个页面会继续解锁学习资源、练习题库、图谱关系和配置检查四个分区。</span>
      </section>

      <div v-if="!createMode" class="content-layout">
        <aside class="content-nav panel-shell" aria-label="内容分区">
          <button
            v-for="card in sectionCards"
            :key="card.key"
            type="button"
            class="content-nav__item"
            :class="{ active: activeSection === card.key }"
            @click="activeSection = card.key"
          >
            <div class="content-nav__item-head">
              <span class="content-nav__icon-wrap" :class="{ active: activeSection === card.key }">
                <el-icon :size="18"><component :is="card.icon" /></el-icon>
              </span>
              <strong>{{ card.title }}</strong>
              <span class="content-nav__count">{{ card.count }}</span>
            </div>
          </button>
        </aside>

        <main class="content-main">
          <template v-if="activeSection === 'basic'">
            <section class="content-card panel-shell">
              <div class="content-card__head">
                <div>
                  <h3>基础信息</h3>
                  <p>定义这个知识点是什么、属于哪里、培养什么能力，是资源和练习配置的前提。</p>
                </div>
                <div class="content-card__head-actions">
                  <el-button :loading="saving" @click="saveKpMeta">保存基础信息</el-button>
                  <el-button @click="activeSection = 'learning'">继续配置资源</el-button>
                </div>
              </div>
              <div class="content-check-grid">
                <article class="check-card">
                  <span>编码</span>
                  <strong>{{ kpForm.code || "未填写" }}</strong>
                </article>
                <article class="check-card">
                  <span>名称</span>
                  <strong>{{ kpForm.title || "未填写" }}</strong>
                </article>
                <article class="check-card">
                  <span>所属分类</span>
                  <strong>{{ kpForm.chapter || "未填写" }}</strong>
                </article>
                <article class="check-card">
                  <span>难度 / 重要度</span>
                  <strong>{{ Math.round(kpForm.difficulty * 100) }}% / {{ Math.round(kpForm.importance * 100) }}%</strong>
                </article>
              </div>
              <div class="content-tags-panel">
                <div class="content-tags-panel__group">
                  <span>知识目标</span>
                  <div class="content-tags"><span class="content-chip">{{ kpForm.knowledge_tag || "未填写知识目标" }}</span></div>
                </div>
                <div class="content-tags-panel__group">
                  <span>能力标签</span>
                  <div class="content-tags"><span class="content-chip">{{ kpForm.ability_tag || "未填写能力标签" }}</span></div>
                </div>
                <div class="content-tags-panel__group">
                  <span>素养标签</span>
                  <div class="content-tags"><span class="content-chip">{{ kpForm.literacy_tag || "未填写素养标签" }}</span></div>
                </div>
              </div>
              <div class="content-empty">{{ kpForm.description || "建议补充知识点描述，方便学生端理解学习目标和学习方式。" }}</div>
            </section>
          </template>

          <template v-else-if="activeSection === 'learning'">
            <section class="content-card panel-shell">
              <div class="content-card__head">
                <div>
                  <h3>学习资料</h3>
                  <p>上传或挂接视频、文档、课件与外链。可同时配置学生学习资源和推荐拓展资源。</p>
                </div>
                <div class="content-card__head-actions">
                  <el-button type="primary" @click="openResourceCreate('learning')">新增学习资源</el-button>
                  <el-button @click="openResourceCreate('recommend')">新增推荐资源</el-button>
                </div>
              </div>
              <div v-if="learningResources.length === 0 && recommendResources.length === 0" class="content-empty">还没有学习资源或推荐拓展</div>
              <el-tabs v-else v-model="teacherResourceView" class="teacher-resource-tabs">
                <el-tab-pane label="全部资源一览" name="all">
                  <div class="content-list content-list--scroll">
                    <div v-for="item in [...allLearningResourcesSorted, ...recommendResources]" :key="`${item.category}-${item.id}`" class="content-item">
                      <div class="content-item__body">
                        <div class="content-item__meta">
                          <div class="content-badge">{{ resourceTypeLabel(item.detected_resource_type || item.type) }}</div>
                          <div class="content-badge">{{ (item.category || 'learning') === 'recommend' ? '推荐拓展' : '学习资源' }}</div>
                          <div class="content-status" :class="`content-status--${item.preview_status || 'ready'}`">
                            {{ previewStatusLabel(item.preview_status) }}
                          </div>
                        </div>
                        <strong>{{ item.title }}</strong>
                        <span>
                          原始格式：{{ (item.file_extension || "").replace('.', '').toUpperCase() || resourceTypeLabel(item.type) }}
                          · 预览方式：{{ previewLabel(item) }}
                        </span>
                        <span v-if="item.original_file_name">{{ item.original_file_name }}</span>
                        <span v-if="item.preview_error" class="content-error">{{ item.preview_error }}</span>
                      </div>
                      <div class="content-item__actions">
                        <el-button size="small" type="primary" plain @click="openResourceEdit(item, (item.category || 'learning') === 'recommend' ? 'recommend' : 'learning')">编辑</el-button>
                        <el-button size="small" @click="openResourceDetail(item.id)">详细配置</el-button>
                        <el-dropdown trigger="click" @command="(cmd) => handleResourceMoreCommand(String(cmd), item)">
                          <el-button size="small">
                            更多
                            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                          </el-button>
                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item command="preview" :disabled="item.preview_status === 'processing'">预览</el-dropdown-item>
                              <el-dropdown-item command="original">下载原文件</el-dropdown-item>
                              <el-dropdown-item command="remove" divided class="resource-dropdown-danger">删除</el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>
                <el-tab-pane label="按类型分组" name="grouped">
                  <div class="content-group-list">
                    <section v-for="group in groupedLearningResources" :key="group.key" class="content-group">
                      <div class="content-group__head">
                        <strong>{{ group.title }}</strong>
                        <span>{{ group.items.length }} 个</span>
                      </div>
                      <div class="content-list">
                        <div v-for="item in group.items" :key="item.id" class="content-item">
                          <div class="content-item__body">
                            <div class="content-item__meta">
                              <div class="content-badge">{{ resourceTypeLabel(item.detected_resource_type || item.type) }}</div>
                              <div class="content-status" :class="`content-status--${item.preview_status || 'ready'}`">{{ previewStatusLabel(item.preview_status) }}</div>
                            </div>
                            <strong>{{ item.title }}</strong>
                          </div>
                          <div class="content-item__actions">
                            <el-button size="small" type="primary" plain @click="openResourceEdit(item, 'learning')">编辑</el-button>
                            <el-button size="small" @click="openResourceDetail(item.id)">详细配置</el-button>
                          </div>
                        </div>
                      </div>
                    </section>
                    <section class="content-group">
                      <div class="content-group__head">
                        <strong>推荐拓展</strong>
                        <span>{{ recommendResources.length }} 个</span>
                      </div>
                      <div v-if="recommendResources.length === 0" class="content-empty">还没有推荐拓展资源</div>
                      <div v-else class="content-list">
                        <div v-for="item in recommendResources" :key="item.id" class="content-item">
                          <div class="content-item__body">
                            <div class="content-item__meta">
                              <div class="content-badge">{{ resourceTypeLabel(item.detected_resource_type || item.type) }}</div>
                              <div class="content-status" :class="`content-status--${item.preview_status || 'ready'}`">{{ previewStatusLabel(item.preview_status) }}</div>
                            </div>
                            <strong>{{ item.title }}</strong>
                          </div>
                          <div class="content-item__actions">
                            <el-button size="small" type="primary" plain @click="openResourceEdit(item, 'recommend')">编辑</el-button>
                            <el-button size="small" @click="openResourceDetail(item.id)">详细配置</el-button>
                          </div>
                        </div>
                      </div>
                    </section>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </section>
          </template>

          <template v-else-if="activeSection === 'practice'">
            <section class="content-card panel-shell">
              <div class="content-card__head">
                <div>
                  <h3>题库</h3>
                  <p>维护本知识点下的题目，并标注认知层级与能力标签；下方“已加入的练习”决定学生端练习顺序。</p>
                </div>
                <el-button type="primary" @click="openQuestionCreate">新增题目</el-button>
              </div>

              <div v-if="questions.length === 0" class="content-empty">当前知识点还没有题目</div>
              <div v-else class="content-list">
                <div v-for="item in questions" :key="item.id" class="content-item">
                  <div class="content-item__body">
                    <div class="content-badge">{{ questionTypeLabel(item.type) }}</div>
                    <strong>{{ item.prompt }}</strong>
                    <span>
                      难度 {{ Math.round((item.difficulty || 0) * 100) }}% · 认知：{{ cognitiveLabel(item.cognitive_level) }}
                      <template v-if="item.ability_subtags"> · 能力标签：{{ item.ability_subtags }}</template>
                      · {{ assignedQuestionIds.has(item.id) ? "已加入练习" : "未加入练习" }}
                    </span>
                  </div>
                  <div class="content-item__actions">
                    <el-button size="small" @click="openQuestionEdit(item)">编辑</el-button>
                    <el-button v-if="!assignedQuestionIds.has(item.id)" size="small" @click="assignQuestionToPractice(item.id)">加入练习</el-button>
                    <el-button size="small" type="danger" @click="removeQuestion(item.id)">删除</el-button>
                  </div>
                </div>
              </div>
            </section>

            <section class="content-card panel-shell">
              <div class="content-card__head">
                <div>
                  <h3>已加入的练习</h3>
                  <p>这里的题会进入学生端练习流，学生可以按知识点完成练习。</p>
                </div>
              </div>
              <div v-if="assignedPractice.length === 0" class="content-empty">还没有加入练习的题目</div>
              <div v-else class="content-list">
                <div v-for="item in assignedPractice" :key="item.id" class="content-item">
                  <div class="content-item__body">
                    <div class="content-badge">第 {{ item.order }} 题</div>
                    <strong>{{ item.prompt }}</strong>
                    <span>{{ questionTypeLabel(item.type) }}</span>
                  </div>
                  <div class="content-item__actions">
                    <el-button size="small" type="danger" @click="removeAssignedPractice(item.id)">移出练习</el-button>
                  </div>
                </div>
              </div>
            </section>
          </template>

          <template v-else-if="activeSection === 'relation'">
            <section class="content-card panel-shell">
              <div class="content-card__head">
                <div>
                  <h3>图谱关系</h3>
                  <p>配置当前知识点和其他知识点的前置、后继、关联、支撑与包含关系，决定图谱结构和学习路径。</p>
                </div>
              </div>

              <div class="relation-create">
                <el-form-item label="关系类型">
                  <el-select v-model="relationForm.relationType" style="width: 100%">
                    <el-option label="前置 / 后继" value="prerequisite" />
                    <el-option label="关联" value="related" />
                    <el-option label="支撑" value="support" />
                    <el-option label="包含" value="contains" />
                  </el-select>
                </el-form-item>
                <el-form-item label="关系方向">
                  <el-segmented
                    v-model="relationForm.direction"
                    :options="[
                      { label: '当前点 -> 目标点', value: 'outgoing' },
                      { label: '目标点 -> 当前点', value: 'incoming' },
                    ]"
                  />
                </el-form-item>
                <el-form-item label="目标知识点">
                  <el-select v-model="relationForm.targetId" filterable style="width: 100%" placeholder="选择要建立关系的知识点">
                    <el-option v-for="item in relationOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
                <div class="relation-create__actions">
                  <el-button type="primary" :loading="relationSaving" @click="createRelation">添加关系</el-button>
                </div>
              </div>

              <div class="relation-grid">
                <section class="relation-panel">
                  <div class="relation-panel__head"><strong>前置知识点</strong><span>{{ relationSummary.prerequisitesIn.length }}</span></div>
                  <div v-if="relationSummary.prerequisitesIn.length === 0" class="content-empty">当前没有前置知识点</div>
                  <div v-else class="relation-list">
                    <div v-for="item in relationSummary.prerequisitesIn" :key="`pre-in-${item.edgeId}`" class="relation-item">
                      <div><strong>{{ item.node?.title }}</strong><span>{{ item.node?.code }} · {{ item.text }}</span></div>
                      <el-button type="danger" plain size="small" @click="removeRelation(item.edgeId)">删除</el-button>
                    </div>
                  </div>
                </section>
                <section class="relation-panel">
                  <div class="relation-panel__head"><strong>后继知识点</strong><span>{{ relationSummary.prerequisitesOut.length }}</span></div>
                  <div v-if="relationSummary.prerequisitesOut.length === 0" class="content-empty">当前没有后继知识点</div>
                  <div v-else class="relation-list">
                    <div v-for="item in relationSummary.prerequisitesOut" :key="`pre-out-${item.edgeId}`" class="relation-item">
                      <div><strong>{{ item.node?.title }}</strong><span>{{ item.node?.code }} · {{ item.text }}</span></div>
                      <el-button type="danger" plain size="small" @click="removeRelation(item.edgeId)">删除</el-button>
                    </div>
                  </div>
                </section>
                <section class="relation-panel">
                  <div class="relation-panel__head"><strong>关联知识点</strong><span>{{ relationSummary.related.length }}</span></div>
                  <div v-if="relationSummary.related.length === 0" class="content-empty">当前没有关联知识点</div>
                  <div v-else class="relation-list">
                    <div v-for="item in relationSummary.related" :key="`related-${item.edgeId}`" class="relation-item">
                      <div><strong>{{ item.node?.title }}</strong><span>{{ item.node?.code }} · {{ item.text }}</span></div>
                      <el-button type="danger" plain size="small" @click="removeRelation(item.edgeId)">删除</el-button>
                    </div>
                  </div>
                </section>
                <section class="relation-panel">
                  <div class="relation-panel__head"><strong>支撑 / 包含关系</strong><span>{{ relationSummary.support.length + relationSummary.contains.length }}</span></div>
                  <div v-if="relationSummary.support.length === 0 && relationSummary.contains.length === 0" class="content-empty">当前没有支撑或包含关系</div>
                  <div v-else class="relation-list">
                    <div v-for="item in relationSummary.support" :key="`support-${item.edgeId}`" class="relation-item">
                      <div><strong>{{ item.node?.title }}</strong><span>{{ item.node?.code }} · {{ item.text }}</span></div>
                      <el-button type="danger" plain size="small" @click="removeRelation(item.edgeId)">删除</el-button>
                    </div>
                    <div v-for="item in relationSummary.contains" :key="`contains-${item.edgeId}`" class="relation-item">
                      <div><strong>{{ item.node?.title }}</strong><span>{{ item.node?.code }} · {{ item.text }}</span></div>
                      <el-button type="danger" plain size="small" @click="removeRelation(item.edgeId)">删除</el-button>
                    </div>
                  </div>
                </section>
              </div>
            </section>
          </template>

          <template v-else-if="activeSection === 'check'">
            <section class="content-card panel-shell">
              <div class="content-card__head">
                <div>
                  <h3>配置检查</h3>
                  <p>检查这个知识点是否已形成“基础信息 + 学习资源 + 练习题库 + 图谱关系”的完整闭环。</p>
                </div>
                <div class="content-card__head-actions">
                  <el-button @click="openStudentPreview">查看学生端预览</el-button>
                  <el-button type="primary" :loading="saving" @click="saveAndBack">保存并返回图谱</el-button>
                </div>
              </div>

              <div class="check-overview">
                <div class="check-overview__score">
                  <span>当前完整度</span>
                  <strong>{{ completenessScore }}%</strong>
                </div>
                <div class="check-overview__summary">
                  <strong>{{ missingChecklistItems.length === 0 ? "这个知识点已经可以进入学生端使用" : "还有以下配置项待补充" }}</strong>
                  <span v-if="missingChecklistItems.length === 0">基础信息、学习资源、练习题和图谱关系都已配置完成。</span>
                  <span v-else>{{ missingChecklistItems.map((item) => item.label).join("、") }}</span>
                </div>
              </div>

              <div class="check-list">
                <article v-for="item in checklistItems" :key="item.key" class="check-list__item" :class="{ done: item.done }">
                  <div class="check-list__copy">
                    <strong>{{ item.label }}</strong>
                    <span>{{ item.detail }}</span>
                  </div>
                  <div class="check-list__actions">
                    <span class="check-list__status">{{ item.done ? "已完成" : "待补充" }}</span>
                    <el-button
                      v-if="!item.done"
                      size="small"
                      @click="jumpToSection(item.key === 'relation' ? 'relation' : item.key === 'learning' || item.key === 'recommend' ? 'learning' : item.key === 'practice' || item.key === 'practiceAssigned' ? 'practice' : 'basic')"
                    >
                      去处理
                    </el-button>
                  </div>
                </article>
              </div>
            </section>
          </template>
        </main>
      </div>
    </div>

    <el-dialog
      v-model="resourceDialogOpen"
      :title="resourceDialogTitle"
      width="1120px"
      class="resource-upload-dialog"
    >
      <div class="resource-upload-dialog__layout">
        <section class="resource-upload-dialog__main">
          <el-form label-position="top" class="resource-form">
            <div class="resource-form__row">
              <el-form-item label="资源来源">
                <el-radio-group v-model="resourceForm.source_kind" :disabled="Boolean(resourceEditingId)">
                  <el-radio label="upload">上传文件</el-radio>
                  <el-radio label="external">外部链接</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="所属分类">
                <el-radio-group v-model="resourceForm.category">
                  <el-radio label="learning">学习内容</el-radio>
                  <el-radio label="recommend">推荐资源</el-radio>
                </el-radio-group>
              </el-form-item>
            </div>

            <el-form-item required>
              <template #label>
                <div class="resource-form__label">资源名称</div>
              </template>
              <el-input v-model="resourceForm.title" placeholder="例如：操作系统概念导学、同步与互斥讲解视频" />
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="resource-form__label">
                  所属知识点
                  <span class="resource-form__label-hint">当前页面已固定到这个知识点</span>
                </div>
              </template>
              <el-input :model-value="currentKpLabel" disabled />
            </el-form-item>

            <el-form-item label="资源描述">
              <el-input
                v-model="resourceForm.description"
                type="textarea"
                :rows="4"
                placeholder="告诉学生这份资源适合怎么学、适合哪个阶段看。"
              />
              <div class="resource-form__counter">{{ resourceDescriptionCount }}/200</div>
            </el-form-item>

            <el-form-item label="标签">
              <el-input v-model="resourceForm.tags" placeholder="例如：必学、章节重点、实验前阅读" />
            </el-form-item>
            <div v-if="resourceTagPreview.length" class="resource-tag-preview">
              <span v-for="tag in resourceTagPreview" :key="tag" class="resource-tag-preview__item">{{ tag }}</span>
            </div>

            <template v-if="resourceForm.source_kind === 'upload'">
              <div
                class="resource-upload-dropzone"
                :class="{ 'resource-upload-dropzone--active': resourceDragActive }"
                @dragenter.prevent="handleUploadDragEnter"
                @dragover.prevent="handleUploadDragEnter"
                @dragleave.prevent="handleUploadDragLeave"
                @drop.prevent="handleUploadDrop"
              >
                <div class="resource-upload-dropzone__icon" aria-hidden="true">
                  <el-icon :size="28"><Upload /></el-icon>
                </div>
                <div class="resource-upload-dropzone__title">把文件拖到这里，或点击选择文件</div>
                <div class="resource-upload-dropzone__hint">文档、视频、图片会按类型分别校验。建议视频使用 MP4 / WebM，文档优先 PDF。</div>
                <label class="resource-upload-dropzone__button">
                  选择文件
                  <input
                    class="resource-file-input"
                    type="file"
                    @change="handleUploadChange"
                    :disabled="Boolean(resourceEditingId)"
                  />
                </label>
              </div>
              <el-alert class="resource-upload-limits" type="info" :closable="false" show-icon>
                <template #title>上传限制与视频建议（与后端校验一致）</template>
                <ul class="resource-upload-limits__ul">
                  <li>PDF≤25MB；Word≤25MB；PPT/PPTX≤60MB；图片≤10MB；视频≤300MB。</li>
                  <li>教学视频建议 MP4 / WebM，画面优先 <strong>16:9 横屏</strong>（如 1920×1080）；竖屏或过窄画面在教室大屏体验较差。</li>
                  <li>大文件请保持网络稳定；失败时可重新选择同一文件重试，避免一次批量过多超大文件。</li>
                </ul>
              </el-alert>
              <div v-if="resourceUploadFile || detectedUpload?.original_file_name" class="resource-selected-file">
                <div class="resource-selected-file__name">
                  {{ resourceUploadFile?.name || detectedUpload?.original_file_name }}
                </div>
                <el-button text type="primary" @click="resourceUploadFile = null; detectedUpload = null; clientUploadMeta = null">重新选择</el-button>
              </div>
            </template>
            <el-form-item v-else label="资源 URL / 外部地址">
              <el-input v-model="resourceForm.url" placeholder="可填写 B 站、课程网站、公开学习链接，系统只保存跳转地址" />
            </el-form-item>
          </el-form>
        </section>

        <aside class="resource-upload-dialog__aside">
          <div class="resource-detect-card resource-detect-card--sticky">
            <div class="resource-detect-card__title">系统识别结果</div>
            <div v-if="detectedUpload" class="resource-detect-grid resource-detect-grid--single">
              <div><span>原始文件名</span><strong>{{ detectedUpload.original_file_name }}</strong></div>
              <div><span>文件后缀</span><strong>{{ detectedUpload.file_extension || "无" }}</strong></div>
              <div><span>MIME 类型</span><strong>{{ detectedUpload.detected_mime_type }}</strong></div>
              <div><span>系统识别类型</span><strong>{{ resourceTypeLabel(detectedUpload.detected_resource_type) }}</strong></div>
              <div><span>学生预览方式</span><strong>{{ detectedUpload.preview_label }}</strong></div>
              <div><span>预览版本</span><strong>{{ detectedUpload.preview_type === "pdf_after_convert" ? "转换为 PDF 在线预览" : "原文件直接预览" }}</strong></div>
              <div v-if="detectedUpload.upload_rule?.max_size_bytes"><span>大小限制</span><strong>{{ Math.round((detectedUpload.upload_rule.max_size_bytes || 0) / 1024 / 1024) }} MB</strong></div>
              <div v-if="clientUploadMeta?.width && clientUploadMeta?.height"><span>画面尺寸</span><strong>{{ clientUploadMeta.width }} × {{ clientUploadMeta.height }}</strong></div>
              <div v-if="clientUploadMeta?.duration"><span>视频时长</span><strong>{{ Math.round(clientUploadMeta.duration) }} 秒</strong></div>
            </div>
            <div v-else class="resource-detect-card__empty">
              选择文件后，这里会显示系统识别出的真实类型、学生预览方式和转换结果。
            </div>
            <div v-if="detectedUpload?.extension_mismatch" class="resource-detect-card__warning">
              检测到文件扩展名与真实类型不一致，请确认文件来源。
            </div>
            <div v-if="clientUploadMeta?.warnings?.length" class="resource-detect-card__warning">
              <div v-for="warning in clientUploadMeta.warnings" :key="warning">{{ warning }}</div>
            </div>
          </div>

          <div class="resource-detect-card">
            <div class="resource-detect-card__title">预览处理状态</div>
            <div class="resource-preview-flow">
              <div class="resource-preview-flow__status">待校验</div>
              <strong>{{ detectedUpload?.preview_type === "pdf_after_convert" ? "系统将转换为 PDF 供学生在线预览" : "学生将直接预览原文件或打开外部链接" }}</strong>
              <p>
                {{ detectedUpload ? "上传成功后会保存原文件，同时按识别结果生成学生端预览版本。" : "还未选择文件，系统将在上传前自动识别文件类型。" }}
              </p>
            </div>
          </div>
        </aside>
      </div>
      <template #footer>
        <el-button @click="resourceDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveResource">确认上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="questionDialogOpen" :title="questionEditingId ? '编辑练习题' : '新增练习题'" width="720px">
      <el-form label-position="top">
        <el-form-item label="题型">
          <el-select v-model="questionForm.type" style="width: 100%">
            <el-option label="选择题" value="mcq" />
            <el-option label="填空题" value="blank" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干">
          <el-input v-model="questionForm.prompt" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="questionForm.type === 'mcq'" label="选项（每行一个）">
          <el-input v-model="questionForm.options_text" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="questionForm.answer" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="questionForm.explanation" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="难度">
          <el-input-number v-model="questionForm.difficulty" :min="0" :max="1" :step="0.05" />
        </el-form-item>
        <el-form-item label="认知层级（布鲁姆）">
          <el-select v-model="questionForm.cognitive_level" style="width: 100%" placeholder="选择层级">
            <el-option v-for="opt in COGNITIVE_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <div class="resource-form__counter" style="text-align: left; margin-top: 6px">
            高阶题为「应用」及以上；报告里会单独统计高阶题正确率。
          </div>
        </el-form-item>
        <el-form-item label="能力二级标签">
          <el-input
            v-model="questionForm.ability_subtags"
            placeholder="与知识点能力维度一致，逗号分隔，如：逻辑推理,问题分解"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.teacher-content-page {
  min-height: 100vh;
  background: var(--app-bg);
  padding: 20px;
}

.teacher-content-page__inner {
  max-width: 1500px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.content-breadcrumb-wrap {
  padding: 0 2px;
}

.teacher-content-page :deep(.el-breadcrumb__inner) {
  font-weight: 600;
}

.teacher-content-page :deep(.el-breadcrumb__separator) {
  color: #b8c5d8;
}

.content-breadcrumb-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--app-primary);
  font-weight: 700;
  text-decoration: none;
}

.content-breadcrumb-link:hover {
  text-decoration: underline;
}

.content-breadcrumb-icon {
  font-size: 15px;
}

.panel-shell {
  background: #ffffff;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  box-shadow: var(--app-shadow-soft);
}

.content-topbar {
  min-height: 96px;
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.content-topbar__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.content-topbar__left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.content-topbar__titles {
  min-width: 0;
}

.content-back {
  border: 1px solid var(--app-border);
  background: #f7f9fc;
  color: #39506d;
  border-radius: 12px;
  padding: 11px 16px;
  font-weight: 700;
  cursor: pointer;
}

.content-eyebrow {
  display: none;
}

.content-title {
  margin: 4px 0 0;
  font-size: 26px;
  line-height: 1.25;
  color: #1f2d3d;
  letter-spacing: -0.02em;
}

.content-subtitle {
  display: none;
}

.content-kp {
  display: grid;
  justify-items: end;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: linear-gradient(165deg, #fbfdff 0%, #f4f8fc 100%);
  color: #445a78;
  text-align: right;
  max-width: 340px;
  flex-shrink: 0;
}

.content-kp__code {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7f8ea3;
}

.content-kp__title {
  font-size: 16px;
  font-weight: 800;
  color: #1f2f44;
  line-height: 1.35;
}

.content-kp__chapter {
  font-size: 12px;
  color: #7f8ea3;
}

.content-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.content-meta {
  padding: 18px 20px 20px;
  display: grid;
  gap: 16px;
}

.content-meta__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.content-meta__head h3 {
  margin: 0;
  font-size: 18px;
  color: #1f2f44;
}

.content-meta__head p {
  margin: 6px 0 0;
  color: #6c7d95;
  line-height: 1.6;
}

.content-meta__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px 16px;
}

.content-meta__full {
  grid-column: 1 / -1;
}

.content-create-empty {
  padding: 24px;
  display: grid;
  gap: 8px;
  justify-items: start;
  color: #4b627f;
}

.content-create-empty strong {
  font-size: 16px;
  color: #1f2f44;
}

.content-create-empty span {
  line-height: 1.7;
}

.summary-card {
  background: #ffffff;
  border: 1px solid var(--app-border);
  border-radius: 18px;
  padding: 16px 18px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  box-shadow: var(--app-shadow-soft);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.summary-card:hover {
  border-color: color-mix(in srgb, var(--app-primary) 22%, var(--app-border));
  box-shadow: 0 14px 36px rgba(31, 47, 68, 0.06);
}

.summary-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.summary-card__icon--learning {
  background: linear-gradient(145deg, #e8f8ef 0%, #dff5e8 100%);
  color: #1f7a4a;
}

.summary-card__icon--practice {
  background: linear-gradient(145deg, #e8f0ff 0%, #dce8ff 100%);
  color: #2f6fed;
}

.summary-card__icon--basic {
  background: linear-gradient(145deg, #f4f0ff 0%, #ece5ff 100%);
  color: #7251d3;
}

.summary-card__icon--relation {
  background: linear-gradient(145deg, #e9fbf7 0%, #ddf7f0 100%);
  color: #148166;
}

.summary-card__icon--check {
  background: linear-gradient(145deg, #fff4e5 0%, #ffe8cc 100%);
  color: #b86b00;
}

.summary-card__body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.summary-card__label {
  font-size: 13px;
  color: #75879f;
  font-weight: 700;
}

.summary-card__value {
  font-size: 28px;
  font-weight: 800;
  color: #233854;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.summary-card__desc {
  display: none;
}

.content-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 18px;
}

.content-nav {
  padding: 16px 14px 18px;
  display: grid;
  gap: 10px;
  align-content: start;
}

.content-nav__hint {
  display: none;
}

.content-nav__item {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fcfdff;
  color: #4a5d77;
  text-align: left;
  padding: 14px 14px 12px;
  cursor: pointer;
  display: grid;
  gap: 8px;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.content-nav__item:hover {
  border-color: #c8d7e7;
  background: #ffffff;
}

.content-nav__item-head {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.content-nav__item-head strong {
  font-size: 15px;
  flex: 1;
  min-width: 0;
  line-height: 1.3;
}

.content-nav__icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dbe4ef;
  display: grid;
  place-items: center;
  color: #5c7cb2;
  flex-shrink: 0;
}

.content-nav__count {
  font-size: 12px;
  font-weight: 800;
  color: var(--app-primary);
  background: color-mix(in srgb, var(--app-primary) 10%, transparent);
  padding: 3px 9px;
  border-radius: 999px;
}

.content-nav__item small {
  display: none;
}

.content-nav__item.active {
  background: linear-gradient(165deg, #f5f9ff 0%, #eef4fc 100%);
  border-color: color-mix(in srgb, var(--app-primary) 35%, var(--app-border));
  box-shadow: 0 8px 22px rgba(47, 111, 237, 0.08);
  color: #39506d;
}

.content-nav__item.active .content-nav__icon-wrap {
  background: color-mix(in srgb, var(--app-primary) 12%, #ffffff);
  border-color: color-mix(in srgb, var(--app-primary) 45%, #dbe4ef);
  color: var(--app-primary);
}

.content-main {
  display: grid;
  gap: 18px;
  align-content: start;
}

.content-card__head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.content-card {
  padding: 22px;
  display: grid;
  gap: 18px;
}

.content-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  flex-wrap: wrap;
}

.content-card__head h3 {
  margin: 0;
  font-size: 24px;
  color: #223754;
}

.content-card__head p {
  display: none;
}

.content-empty {
  color: #7d8ea4;
  font-size: 15px;
  padding: 18px;
  border: 1px dashed #d6e1ee;
  border-radius: 16px;
  background: #fafbfd;
}

.content-check-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.check-card {
  padding: 16px 18px;
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fcfdff;
  display: grid;
  gap: 6px;
}

.check-card span {
  font-size: 12px;
  color: #7a8ba2;
}

.check-card strong {
  color: #223754;
  font-size: 16px;
}

.content-tags-panel {
  display: grid;
  gap: 14px;
}

.content-tags-panel__group {
  display: grid;
  gap: 8px;
}

.content-tags-panel__group > span {
  font-size: 13px;
  color: #5d708a;
  font-weight: 700;
}

.content-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.content-chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #d7e1ed;
  background: #f6f9fc;
  color: #445a78;
  font-size: 13px;
  font-weight: 700;
}

.content-list {
  display: grid;
  gap: 10px;
}

.content-list--scroll {
  max-height: 520px;
  overflow-y: auto;
  padding-right: 6px;
}

.teacher-resource-tabs :deep(.el-tabs__header) {
  margin-bottom: 14px;
}

.content-group-list {
  display: grid;
  gap: 14px;
}

.content-group {
  border: 1px solid #dce5f0;
  border-radius: 18px;
  background: #fafcff;
  padding: 14px;
  display: grid;
  gap: 12px;
}

.content-group__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.content-group__head strong {
  color: #23405f;
  font-size: 16px;
}

.content-group__head span {
  color: #70819a;
  font-size: 12px;
  font-weight: 700;
}

.content-item {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fcfdff;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.content-item__body {
  display: grid;
  gap: 4px;
}

.content-item__meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.content-item__body strong {
  color: #1f2f44;
  font-size: 18px;
}

.content-item__body span {
  color: #6f7f95;
  font-size: 14px;
  word-break: break-all;
}

.content-error {
  color: #c04b4b !important;
}

.content-item__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
}

.teacher-content-page :deep(.resource-dropdown-danger) {
  color: #c04b4b !important;
}

.content-badge {
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f3f7fc;
  border: 1px solid #d7e1ed;
  color: #4c627d;
  font-size: 12px;
  font-weight: 700;
}

.content-status {
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid var(--app-border);
}

.content-status--processing {
  background: #fff7ea;
  color: #a96a13;
  border-color: #f3d8a6;
}

.content-status--ready {
  background: #eff8f2;
  color: #2f7a47;
  border-color: #cde7d4;
}

.content-status--failed {
  background: #fff0f0;
  color: #c04b4b;
  border-color: #f0c7c7;
}

.teacher-content-page :deep(.el-button) {
  border-radius: 10px;
  font-weight: 700;
}

.teacher-content-page :deep(.el-button--primary) {
  background: #2f6fed;
  border-color: #2f6fed;
}

.teacher-content-page :deep(.el-button--danger) {
  background: #fff1f1;
  border-color: #ffd8d8;
  color: #d24848;
}

.teacher-content-page :deep(.el-dialog) {
  border-radius: 24px;
  overflow: hidden;
}

.teacher-content-page :deep(.el-dialog__header) {
  border-bottom: 1px solid #e7edf5;
  margin-right: 0;
  padding: 24px 28px 18px;
}

.teacher-content-page :deep(.el-dialog__title) {
  font-size: 22px;
  font-weight: 800;
  color: #1f2f44;
}

.teacher-content-page :deep(.el-dialog__body) {
  padding: 0;
}

.teacher-content-page :deep(.el-dialog__footer) {
  border-top: 1px solid #e7edf5;
  padding: 16px 24px 18px;
  background: #fff;
}

.resource-upload-dialog__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
  min-height: 640px;
}

.resource-upload-dialog__main {
  padding: 26px 30px 28px;
  border-right: 1px solid #ecf1f6;
  background: #ffffff;
}

.resource-upload-dialog__aside {
  padding: 26px 24px 28px;
  background: linear-gradient(180deg, #fbfcff 0%, #f8fafc 100%);
  display: grid;
  align-content: start;
  gap: 16px;
}

.resource-form {
  display: grid;
  gap: 6px;
}

.resource-form__row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.resource-form__label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  color: #243854;
}

.resource-form__label-hint {
  display: none;
}

.resource-form__counter {
  margin-top: 8px;
  text-align: right;
  font-size: 12px;
  color: #8595aa;
}

.resource-file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.resource-upload-limits {
  margin-top: 14px;
}
.resource-upload-limits :deep(.el-alert__description) {
  margin: 0;
}
.resource-upload-limits__ul {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  line-height: 1.65;
  color: #4b5f78;
}

.resource-upload-dropzone {
  border: 1px dashed #b9d0f5;
  border-radius: 18px;
  background: linear-gradient(180deg, #f9fbff 0%, #f4f8ff 100%);
  min-height: 200px;
  display: grid;
  justify-items: center;
  align-content: center;
  text-align: center;
  gap: 12px;
  padding: 20px;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.resource-upload-dropzone--active {
  border-color: #2f6fed;
  background: linear-gradient(180deg, #f2f7ff 0%, #eaf2ff 100%);
  box-shadow: 0 0 0 4px rgba(47, 111, 237, 0.08);
  transform: translateY(-1px);
}

.resource-upload-dropzone__icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  background: #e9f1ff;
  color: #2f6fed;
  display: grid;
  place-items: center;
  font-size: 26px;
  font-weight: 700;
}

.resource-upload-dropzone__title {
  font-size: 20px;
  font-weight: 800;
  color: #20324a;
}

.resource-upload-dropzone__hint {
  display: none;
}

.resource-upload-dropzone__button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 18px;
  border-radius: 12px;
  background: #2f6fed;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.resource-selected-file {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid #dbe5f0;
  border-radius: 14px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.resource-selected-file__name {
  color: #223754;
  font-weight: 700;
  word-break: break-all;
}

.resource-tag-preview {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: -6px;
  margin-bottom: 8px;
}

.resource-tag-preview__item {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #dbe4ef;
  background: #f8fafc;
  color: #51657f;
  font-size: 12px;
  font-weight: 700;
}

.resource-detect-card {
  padding: 22px 22px 20px;
  border: 1px solid #e3eaf3;
  border-radius: 18px;
  background: #ffffff;
  display: grid;
  gap: 14px;
  box-shadow: 0 12px 30px rgba(31, 47, 68, 0.04);
}

.resource-detect-card--sticky {
  align-self: start;
}

.resource-detect-card__title {
  font-weight: 800;
  font-size: 16px;
  color: #233854;
}

.resource-detect-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.resource-detect-grid--single {
  grid-template-columns: 1fr;
}

.resource-detect-grid div {
  display: grid;
  gap: 4px;
}

.resource-detect-grid span {
  font-size: 12px;
  color: #7f8ea3;
}

.resource-detect-grid strong {
  color: #243854;
  word-break: break-all;
  line-height: 1.6;
}

.resource-detect-card__empty {
  min-height: 180px;
  display: grid;
  place-items: center;
  text-align: center;
  color: #7c8ca3;
  font-size: 14px;
  line-height: 1.8;
  border: 1px dashed #dbe4ef;
  border-radius: 14px;
  background: #fbfcff;
}

.resource-detect-card__warning {
  color: #b36b00;
  background: #fff8e7;
  border: 1px solid #f2dfaf;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
}

.resource-preview-flow {
  display: grid;
  gap: 10px;
}

.resource-preview-flow__status {
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #fff6e8;
  color: #a86c1d;
  border: 1px solid #f3ddb0;
  font-size: 12px;
  font-weight: 800;
}

.resource-preview-flow strong {
  color: #223754;
  font-size: 17px;
  line-height: 1.6;
}

.resource-preview-flow p {
  margin: 0;
  color: #72839b;
  line-height: 1.8;
  font-size: 14px;
}

.relation-create {
  display: grid;
  grid-template-columns: 1fr auto 1.2fr auto;
  gap: 14px;
  align-items: end;
}

.relation-create__actions {
  display: flex;
  justify-content: flex-end;
}

.relation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.relation-panel {
  border: 1px solid #dce5f0;
  border-radius: 18px;
  background: #fafcff;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.relation-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #223754;
}

.relation-panel__head strong {
  font-size: 16px;
}

.relation-panel__head span {
  font-size: 12px;
  font-weight: 800;
  color: var(--app-primary);
}

.relation-list {
  display: grid;
  gap: 10px;
}

.relation-item {
  padding: 14px 16px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: #ffffff;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.relation-item > div {
  display: grid;
  gap: 4px;
}

.relation-item strong {
  color: #223754;
}

.relation-item span {
  color: #6c7d95;
  font-size: 13px;
}

.check-overview {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  align-items: stretch;
}

.check-overview__score,
.check-overview__summary {
  border: 1px solid var(--app-border);
  border-radius: 18px;
  background: #fcfdff;
  padding: 18px 20px;
}

.check-overview__score {
  display: grid;
  gap: 8px;
}

.check-overview__score span {
  color: #6f8199;
  font-size: 13px;
}

.check-overview__score strong {
  font-size: 42px;
  line-height: 1;
  color: #1f2f44;
}

.check-overview__summary {
  display: grid;
  gap: 8px;
}

.check-overview__summary strong {
  color: #223754;
  font-size: 16px;
}

.check-overview__summary span {
  color: #6f8199;
  line-height: 1.6;
}

.check-list {
  display: grid;
  gap: 10px;
}

.check-list__item {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fcfdff;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
}

.check-list__item.done {
  background: #f2fbf6;
  border-color: #cfe8d7;
}

.check-list__copy {
  display: grid;
  gap: 4px;
}

.check-list__copy strong {
  color: #223754;
}

.check-list__copy span {
  color: #6f8199;
  font-size: 13px;
}

.check-list__actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.check-list__status {
  font-size: 12px;
  font-weight: 800;
  color: #5c708c;
}

@media (max-width: 1120px) {
  .content-summary,
  .content-check-grid,
  .relation-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-layout {
    grid-template-columns: 1fr;
  }

  .content-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-upload-dialog__layout {
    grid-template-columns: 1fr;
  }

  .resource-upload-dialog__main {
    border-right: 0;
    border-bottom: 1px solid #ecf1f6;
  }

  .relation-create,
  .check-overview {
    grid-template-columns: 1fr;
  }

}

@media (max-width: 768px) {
  .content-summary,
  .content-check-grid,
  .relation-grid {
    grid-template-columns: 1fr;
  }

  .content-topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .content-topbar__actions,
  .content-card__head-actions,
  .check-list__actions {
    width: 100%;
    justify-content: flex-start;
  }

  .relation-item,
  .check-list__item {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .teacher-content-page {
    padding: 10px;
  }

  .content-topbar {
    align-items: flex-start;
  }

  .content-topbar__left {
    flex-direction: column;
    align-items: flex-start;
  }

  .content-summary {
    grid-template-columns: 1fr;
  }

  .content-meta__head {
    flex-direction: column;
  }

  .content-meta__grid {
    grid-template-columns: 1fr;
  }

  .content-nav {
    grid-template-columns: 1fr;
  }

  .content-item {
    flex-direction: column;
  }

  .resource-form__row {
    grid-template-columns: 1fr;
  }

  .resource-detect-grid {
    grid-template-columns: 1fr;
  }
}
</style>
