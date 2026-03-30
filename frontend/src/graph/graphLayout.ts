/**
 * 确定性知识图谱布局：基于全量知识点列表，与当前筛选/可见范围无关，
 * 保证教师端、学生端、重新进入页面时坐标一致（除非数据库中保存了教师拖拽坐标）。
 */
export const CANVAS_WIDTH = 60000;
export const CANVAS_HEIGHT = 40000;
export const INITIAL_CENTER_X = 30000;
export const INITIAL_CENTER_Y = 20000;

export type Point = { x: number; y: number };

export type KpLayoutInput = { id: number; code: string; chapter?: string | null };

export function buildDeterministicGraphLayout(kps: KpLayoutInput[]): {
  categoryPositions: Record<string, Point>;
  kpPositions: Record<number, Point>;
} {
  const chapterSet = new Set<string>();
  for (const kp of kps) {
    chapterSet.add(kp.chapter || "未分章");
  }
  const chapters = Array.from(chapterSet).sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));

  const categoryPositions: Record<string, Point> = {};
  const total = Math.max(chapters.length, 1);
  const spread = Math.min(640, Math.max(260, (total - 1) * 200));
  const startX = INITIAL_CENTER_X - spread / 2;
  const step = total === 1 ? 0 : spread / (total - 1);
  chapters.forEach((chapter, index) => {
    categoryPositions[chapter] = {
      x: startX + step * index,
      y: INITIAL_CENTER_Y - 440 + (index % 2 === 0 ? 0 : 52) + index * 10,
    };
  });

  const kpPositions: Record<number, Point> = {};
  const groups = new Map<string, KpLayoutInput[]>();
  for (const kp of kps) {
    const key = kp.chapter || "未分章";
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }

  const gapX = 236;
  const gapY = 198;
  for (const chapter of chapters) {
    const items = groups.get(chapter) ?? [];
    const anchor = categoryPositions[chapter] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
    const ordered = [...items].sort((a, b) => String(a.code || "").localeCompare(String(b.code || ""), "zh-Hans-CN"));
    const columns = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(ordered.length))));
    const startXLocal = anchor.x - ((columns - 1) * gapX) / 2;
    ordered.forEach((kp, index) => {
      const col = index % columns;
      const row = Math.floor(index / columns);
      kpPositions[kp.id] = {
        x: startXLocal + col * gapX + (row % 2 === 0 ? 0 : 20),
        y: anchor.y + 312 + row * gapY,
      };
    });
  }

  return { categoryPositions, kpPositions };
}

/** 新建知识点时替代 Math.random，保证可复现。 */
export function deterministicDraftPosition(seed: string): Point {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const u = (h >>> 0) / 0xffffffff;
  const v = (Math.imul(h, 31) >>> 0) / 0xffffffff;
  return {
    x: INITIAL_CENTER_X + (u - 0.5) * 400,
    y: INITIAL_CENTER_Y + (v - 0.5) * 400,
  };
}

export function mergeChapterLayout(
  base: Record<string, Point>,
  server: Record<string, { x?: number; y?: number }> | null | undefined,
): Record<string, Point> {
  if (!server || typeof server !== "object") return { ...base };
  const next = { ...base };
  for (const [key, val] of Object.entries(server)) {
    const x = Number(val?.x);
    const y = Number(val?.y);
    if (Number.isFinite(x) && Number.isFinite(y)) {
      next[key] = { x, y };
    }
  }
  return next;
}
