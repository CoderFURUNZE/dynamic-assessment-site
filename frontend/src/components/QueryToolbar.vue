<script setup lang="ts">
import { Search } from "@element-plus/icons-vue";
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    hint?: string;
    inputWidth?: string;
    showReset?: boolean;
  }>(),
  {
    placeholder: "请输入关键词",
    hint: "",
    inputWidth: "520px",
    showReset: true,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
  search: [];
  reset: [];
}>();

const displayPlaceholder = computed(() => props.hint || props.placeholder);

function updateValue(value: string) {
  emit("update:modelValue", value);
}
</script>

<template>
  <div class="query-toolbar">
    <div class="query-toolbar__row">
      <div class="query-toolbar__search" :style="{ '--query-input-width': props.inputWidth }">
        <el-input
          :model-value="props.modelValue"
          :placeholder="displayPlaceholder"
          :prefix-icon="Search"
          clearable
          @update:model-value="updateValue"
          @keyup.enter="emit('search')"
          @clear="emit('search')"
        />
      </div>

      <el-button type="primary" class="query-toolbar__btn query-toolbar__btn--primary" @click="emit('search')">查询</el-button>
      <el-button v-if="props.showReset" class="query-toolbar__btn" @click="emit('reset')">重置</el-button>

      <div v-if="$slots.extras" class="query-toolbar__extras">
        <slot name="extras" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.query-toolbar {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.06), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.82) 0%, rgba(248, 251, 255, 0.9) 100%);
}

.query-toolbar__row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.query-toolbar__search {
  flex: 1 1 min(100%, var(--query-input-width));
  width: min(100%, var(--query-input-width));
  min-width: min(100%, 280px);
}

.query-toolbar__search :deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 14px;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.24) inset !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.query-toolbar__search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #60a5fa inset, 0 0 0 4px rgba(96, 165, 250, 0.14) !important;
}

.query-toolbar__search :deep(.el-input__prefix-inner) {
  color: #7a8eaa;
}

.query-toolbar__search :deep(.el-input__inner) {
  font-size: 14px;
  color: var(--app-ink);
}

.query-toolbar__search :deep(.el-input__inner::placeholder) {
  color: #8ea0b8;
}

.query-toolbar__btn {
  min-width: 78px;
  min-height: 40px;
  padding-inline: 14px;
  border-radius: 12px;
  font-weight: 700;
}

.query-toolbar__btn--primary {
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.query-toolbar__extras {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-left: auto;
}

@media (max-width: 768px) {
  .query-toolbar__search {
    width: 100%;
    min-width: 100%;
  }

  .query-toolbar__extras {
    width: 100%;
    margin-left: 0;
  }

  .query-toolbar__btn {
    flex: 1 1 0;
  }
}
</style>
