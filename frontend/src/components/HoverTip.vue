<script setup lang="ts">
withDefaults(defineProps<{
  content: string;
  placement?: "top" | "top-start" | "top-end" | "bottom" | "bottom-start" | "bottom-end" | "left" | "right";
  trigger?: "hover" | "click";
  showAfter?: number;
}>(), {
  placement: "top",
  trigger: "hover",
  showAfter: 300,
});
</script>

<template>
  <el-tooltip :content="content" :placement="placement" :trigger="trigger" :show-after="showAfter">
    <button type="button" class="hover-tip" aria-label="查看提示">
      ?
    </button>
  </el-tooltip>
</template>

<style scoped>
.hover-tip {
  width: 28px;
  height: 28px;
  border: 1px solid #d8e2ef;
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #58729a;
  font-size: 13px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(31, 52, 97, 0.05);
}

.hover-tip:hover {
  color: #2f6fed;
  border-color: #c7d6ea;
}
</style>
