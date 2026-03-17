<script setup lang="ts">
import { computed, ref, watch } from "vue";

type GuideItem = {
  title: string;
  desc: string;
};

type GuideAction = {
  key: string;
  label: string;
  primary?: boolean;
};

const props = defineProps<{
  title: string;
  intro: string;
  items: GuideItem[];
  tips?: string[];
  actions?: GuideAction[];
  storageKey?: string;
}>();

const emit = defineEmits<{
  (e: "action", key: string): void;
}>();

const hidden = ref(false);

const storageToken = computed(() => (props.storageKey ? `da_guide_hidden_${props.storageKey}` : ""));

watch(
  () => props.storageKey,
  () => {
    if (!storageToken.value) {
      hidden.value = false;
      return;
    }
    hidden.value = localStorage.getItem(storageToken.value) === "1";
  },
  { immediate: true },
);

function closeGuide() {
  hidden.value = true;
  if (storageToken.value) localStorage.setItem(storageToken.value, "1");
}

function openGuide() {
  hidden.value = false;
  if (storageToken.value) localStorage.removeItem(storageToken.value);
}
</script>

<template>
  <div class="starter-guide">
    <div v-if="hidden" class="starter-guide__reopen">
      <span>已收起使用说明</span>
      <button @click="openGuide">重新打开</button>
    </div>

    <div v-else class="starter-guide__card">
      <div class="starter-guide__top">
        <div>
          <div class="starter-guide__kicker">先看这里</div>
          <div class="starter-guide__title">{{ title }}</div>
          <div class="starter-guide__intro">{{ intro }}</div>
        </div>
        <button class="starter-guide__close" @click="closeGuide">我知道了</button>
      </div>

      <div class="starter-guide__body">
        <div class="starter-guide__steps">
          <div v-for="(item, index) in items" :key="`${index}-${item.title}`" class="starter-guide__step">
            <strong>{{ index + 1 }}</strong>
            <div>
              <div class="starter-guide__step-title">{{ item.title }}</div>
              <div class="starter-guide__step-desc">{{ item.desc }}</div>
            </div>
          </div>
        </div>

        <div class="starter-guide__side">
          <div v-if="tips?.length" class="starter-guide__tips">
            <div class="starter-guide__side-title">注意事项</div>
            <div v-for="tip in tips" :key="tip" class="starter-guide__tip">{{ tip }}</div>
          </div>

          <div v-if="actions?.length" class="starter-guide__actions">
            <div class="starter-guide__side-title">快速进入</div>
            <div class="starter-guide__action-list">
              <button
                v-for="action in actions"
                :key="action.key"
                class="starter-guide__action"
                :class="{ 'starter-guide__action--primary': action.primary }"
                @click="emit('action', action.key)"
              >
                {{ action.label }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.starter-guide {
  display: grid;
}

.starter-guide__card,
.starter-guide__reopen {
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: none;
}

.starter-guide__card {
  padding: 16px 18px;
  display: grid;
  gap: 14px;
}

.starter-guide__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.starter-guide__kicker {
  font-size: 11px;
  color: var(--app-ink-soft);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.starter-guide__title {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 800;
  color: var(--app-ink);
  letter-spacing: -0.01em;
}

.starter-guide__intro {
  margin-top: 4px;
  max-width: 680px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--app-ink-soft);
}

.starter-guide__close,
.starter-guide__reopen button,
.starter-guide__action {
  border: 1px solid var(--app-border);
  border-radius: 999px;
  background: #fff;
  color: var(--app-ink);
  cursor: pointer;
  font-weight: 700;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.starter-guide__close,
.starter-guide__reopen button {
  padding: 8px 12px;
  white-space: nowrap;
}

.starter-guide__close:hover,
.starter-guide__reopen button:hover,
.starter-guide__action:hover {
  background: var(--app-bg-alt);
}

.starter-guide__body {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
  gap: 14px;
}

.starter-guide__steps {
  display: grid;
  gap: 10px;
}

.starter-guide__step {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 10px;
  align-items: start;
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid var(--app-border);
}

.starter-guide__step strong {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: #eef4ff;
  color: #fff;
  font-size: 15px;
  color: var(--app-green-dark);
}

.starter-guide__step-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
}

.starter-guide__step-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-ink-soft);
}

.starter-guide__side {
  display: grid;
  gap: 10px;
}

.starter-guide__tips,
.starter-guide__actions {
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid var(--app-border);
}

.starter-guide__side-title {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 800;
  color: var(--app-ink);
}

.starter-guide__tip {
  position: relative;
  padding-left: 14px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-ink-soft);
}

.starter-guide__tip + .starter-guide__tip {
  margin-top: 6px;
}

.starter-guide__tip::before {
  content: "";
  position: absolute;
  left: 0;
  top: 9px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--app-green);
}

.starter-guide__action-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.starter-guide__action {
  min-height: 36px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  line-height: 1;
}

.starter-guide__action--primary {
  background: var(--app-green);
  border-color: var(--app-green);
  color: #fff;
}

.starter-guide__action--primary:hover {
  background: #489862;
  border-color: #489862;
}

.starter-guide__reopen {
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  color: var(--app-ink-soft);
}

@media (max-width: 980px) {
  .starter-guide__top,
  .starter-guide__body,
  .starter-guide__reopen {
    grid-template-columns: 1fr;
    display: grid;
  }

  .starter-guide__top {
    gap: 10px;
  }

  .starter-guide__reopen {
    justify-content: start;
  }
}
</style>
