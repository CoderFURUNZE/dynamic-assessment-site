import { ref } from 'vue';

// 全局加载状态
const isLoading = ref(false);
let loadingCount = 0;

// 开始加载
export function startLoading() {
  loadingCount++;
  isLoading.value = true;
}

// 结束加载
export function endLoading() {
  loadingCount--;
  if (loadingCount <= 0) {
    loadingCount = 0;
    isLoading.value = false;
  }
}

// 重置加载状态
export function resetLoading() {
  loadingCount = 0;
  isLoading.value = false;
}

export { isLoading };