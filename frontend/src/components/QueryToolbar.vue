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
}

.query-toolbar__row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  padding: 2px 0;
}

.query-toolbar__search {
  width: min(100%, var(--query-input-width));
  min-width: min(100%, 320px);
}

.query-toolbar__search :deep(.el-input__wrapper) {
  min-height: 46px;
  border-radius: 18px;
  box-shadow: 0 0 0 1px #cfe0fb inset, 0 10px 22px rgba(80, 118, 183, 0.06) !important;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8ff 100%);
}

.query-toolbar__search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #7aa8ff inset, 0 0 0 3px rgba(122, 168, 255, 0.12), 0 12px 24px rgba(80, 118, 183, 0.08) !important;
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
  min-width: 96px;
  min-height: 46px;
  padding-inline: 20px;
  border-radius: 18px;
  font-weight: 700;
}

.query-toolbar__btn--primary {
  box-shadow: 0 10px 24px rgba(79, 140, 255, 0.2);
}

.query-toolbar__extras {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .query-toolbar__search {
    width: 100%;
    min-width: 100%;
  }

  .query-toolbar__extras {
    width: 100%;
  }
}
</style>
