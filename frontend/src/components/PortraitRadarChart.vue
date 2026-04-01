<script setup lang="ts">
import { computed } from "vue";

type RadarItem = {
  dimension_title: string;
  score: number | null;
  available?: boolean;
};

const props = withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string;
    items: RadarItem[];
    accent?: string;
    emptyText?: string;
  }>(),
  {
    title: "五维雷达图",
    subtitle: "",
    accent: "#5c7cff",
    emptyText: "暂无足够数据生成雷达图",
  }
);

const chartSize = 320;
const center = chartSize / 2;
const radius = 106;
const levels = 4;

const normalizedItems = computed(() =>
  (props.items ?? []).map((item) => ({
    ...item,
    score:
      item.score == null || Number.isNaN(Number(item.score))
        ? null
        : Math.max(0, Math.min(1, Number(item.score))),
  }))
);

const hasData = computed(() => normalizedItems.value.some((item) => item.score != null));

function getPoint(index: number, total: number, scale: number) {
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(total, 1);
  return {
    x: center + Math.cos(angle) * radius * scale,
    y: center + Math.sin(angle) * radius * scale,
  };
}

const levelPolygons = computed(() => {
  const total = normalizedItems.value.length;
  return Array.from({ length: levels }, (_, idx) => {
    const scale = (idx + 1) / levels;
    return normalizedItems.value
      .map((_, itemIndex) => {
        const point = getPoint(itemIndex, total, scale);
        return `${point.x},${point.y}`;
      })
      .join(" ");
  });
});

const axisLines = computed(() => {
  const total = normalizedItems.value.length;
  return normalizedItems.value.map((_, index) => {
    const point = getPoint(index, total, 1);
    return {
      x1: center,
      y1: center,
      x2: point.x,
      y2: point.y,
    };
  });
});

const dataPolygon = computed(() => {
  const total = normalizedItems.value.length;
  return normalizedItems.value
    .map((item, index) => {
      const point = getPoint(index, total, item.score ?? 0);
      return `${point.x},${point.y}`;
    })
    .join(" ");
});

const labelPoints = computed(() => {
  const total = normalizedItems.value.length;
  return normalizedItems.value.map((item, index) => {
    const point = getPoint(index, total, 1.2);
    return {
      ...item,
      x: point.x,
      y: point.y,
    };
  });
});
</script>

<template>
  <section class="radar-card">
    <div class="radar-card__head">
      <div>
        <div class="radar-card__title">{{ title }}</div>
      </div>
    </div>

    <div v-if="hasData && items.length >= 3" class="radar-card__body">
      <svg :viewBox="`0 0 ${chartSize} ${chartSize}`" class="radar-svg" role="img" :aria-label="title">
        <polygon
          v-for="(polygon, index) in levelPolygons"
          :key="`level-${index}`"
          :points="polygon"
          class="radar-svg__grid"
        />
        <line
          v-for="(axis, index) in axisLines"
          :key="`axis-${index}`"
          :x1="axis.x1"
          :y1="axis.y1"
          :x2="axis.x2"
          :y2="axis.y2"
          class="radar-svg__axis"
        />
        <polygon :points="dataPolygon" class="radar-svg__data-fill" :style="{ '--radar-accent': accent }" />
        <polygon :points="dataPolygon" class="radar-svg__data-stroke" :style="{ '--radar-accent': accent }" />
        <circle
          v-for="(item, index) in normalizedItems"
          :key="`dot-${index}`"
          :cx="getPoint(index, normalizedItems.length, item.score ?? 0).x"
          :cy="getPoint(index, normalizedItems.length, item.score ?? 0).y"
          r="4.5"
          class="radar-svg__dot"
          :style="{ '--radar-accent': accent }"
        />
        <text
          v-for="item in labelPoints"
          :key="`label-${item.dimension_title}`"
          :x="item.x"
          :y="item.y"
          class="radar-svg__label"
          text-anchor="middle"
        >
          {{ item.dimension_title }}
        </text>
      </svg>

      <div class="radar-legend">
        <div v-for="item in normalizedItems" :key="item.dimension_title" class="radar-legend__item">
          <span class="radar-legend__label">{{ item.dimension_title }}</span>
          <strong class="radar-legend__value">
            {{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}
          </strong>
        </div>
      </div>
    </div>

    <div v-else class="radar-card__empty">{{ emptyText }}</div>
  </section>
</template>

<style scoped>
.radar-card {
  display: grid;
  gap: 16px;
}

.radar-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.radar-card__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-ink, #24324a);
}

.radar-card__body {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(180px, 1fr);
  gap: 18px;
  align-items: center;
}

.radar-svg {
  width: 100%;
  max-width: 320px;
  height: auto;
  overflow: visible;
}

.radar-svg__grid {
  fill: rgba(92, 124, 255, 0.04);
  stroke: rgba(92, 124, 255, 0.16);
  stroke-width: 1;
}

.radar-svg__axis {
  stroke: rgba(92, 124, 255, 0.18);
  stroke-width: 1;
}

.radar-svg__data-fill {
  fill: color-mix(in srgb, var(--radar-accent) 18%, transparent);
  stroke: none;
}

.radar-svg__data-stroke {
  fill: none;
  stroke: var(--radar-accent);
  stroke-width: 2.5;
}

.radar-svg__dot {
  fill: var(--radar-accent);
  stroke: #fff;
  stroke-width: 2;
}

.radar-svg__label {
  font-size: 12px;
  fill: #506784;
  font-weight: 600;
  dominant-baseline: middle;
}

.radar-legend {
  display: grid;
  gap: 10px;
}

.radar-legend__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fbff;
  border: 1px solid var(--app-border);
}

.radar-legend__label {
  font-size: 13px;
  color: var(--app-ink);
}

.radar-legend__value {
  font-size: 14px;
  color: #254d8a;
}

.radar-card__empty {
  min-height: 220px;
  display: grid;
  place-items: center;
  color: var(--app-ink-soft);
  border-radius: 16px;
  background: #fcfdff;
  border: 1px dashed var(--app-border);
}
</style>
