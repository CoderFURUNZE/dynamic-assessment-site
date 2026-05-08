/**
 * Deterministic knowledge graph layout.
 *
 * The teacher workspace can still persist manually dragged positions, but the
 * fallback layout must stay readable for large verified courses.
 */
export const CANVAS_WIDTH = 60000;
export const CANVAS_HEIGHT = 40000;
export const INITIAL_CENTER_X = 30000;
export const INITIAL_CENTER_Y = 20000;

export type Point = { x: number; y: number };

export type KpLayoutInput = { id: number; code: string; chapter?: string | null };

const FALLBACK_CHAPTER = "未分章";

function chapterKey(kp: KpLayoutInput) {
  return kp.chapter || FALLBACK_CHAPTER;
}

function codeOrder(code: string | null | undefined) {
  const match = String(code || "").match(/(\d+)/);
  return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
}

export function buildDeterministicGraphLayout(kps: KpLayoutInput[]): {
  categoryPositions: Record<string, Point>;
  kpPositions: Record<number, Point>;
} {
  const groups = new Map<string, KpLayoutInput[]>();
  for (const kp of kps) {
    const key = chapterKey(kp);
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }

  const chapters = Array.from(groups.keys()).sort((a, b) => {
    const minA = Math.min(...(groups.get(a) ?? []).map((kp) => codeOrder(kp.code)));
    const minB = Math.min(...(groups.get(b) ?? []).map((kp) => codeOrder(kp.code)));
    if (minA !== minB) return minA - minB;
    return a.localeCompare(b, "zh-Hans-CN");
  });

  const categoryPositions: Record<string, Point> = {};
  const total = Math.max(chapters.length, 1);
  const chapterColumns = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(total * 1.35))));
  const chapterRows = Math.ceil(total / chapterColumns);
  const chapterGapX = 1480;
  const chapterGapY = 900;
  const gridWidth = (chapterColumns - 1) * chapterGapX;
  const gridHeight = (chapterRows - 1) * chapterGapY;

  chapters.forEach((chapter, index) => {
    const col = index % chapterColumns;
    const row = Math.floor(index / chapterColumns);
    categoryPositions[chapter] = {
      x: INITIAL_CENTER_X - gridWidth / 2 + col * chapterGapX,
      y: INITIAL_CENTER_Y - gridHeight / 2 + row * chapterGapY,
    };
  });

  const kpPositions: Record<number, Point> = {};
  const gapX = 290;
  const gapY = 216;

  for (const chapter of chapters) {
    const items = groups.get(chapter) ?? [];
    const anchor = categoryPositions[chapter] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
    const ordered = [...items].sort((a, b) => String(a.code || "").localeCompare(String(b.code || ""), "zh-Hans-CN"));
    const columns = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(ordered.length * 0.9))));
    const startXLocal = anchor.x - ((columns - 1) * gapX) / 2;

    ordered.forEach((kp, index) => {
      const col = index % columns;
      const row = Math.floor(index / columns);
      kpPositions[kp.id] = {
        x: startXLocal + col * gapX + (row % 2 === 0 ? 0 : 24),
        y: anchor.y + 220 + row * gapY,
      };
    });
  }

  return { categoryPositions, kpPositions };
}

/** Stable draft position for newly created nodes. */
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
