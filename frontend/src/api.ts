import axios from "axios";
import { getToken } from "./token";
import { startLoading, endLoading } from "./loading";

// 缓存机制
const cache: Record<string, { data: any; timestamp: number }> = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5分钟缓存

// 重试机制
const MAX_RETRIES = 3;
const defaultApiBaseUrl =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000/api`
    : "http://localhost:8000/api";

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL as string | undefined) || defaultApiBaseUrl,
  timeout: 10000, // 10秒超时
});

// 请求拦截器
api.interceptors.request.use((config) => {
  startLoading();
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
}, (error) => {
  endLoading();
  return Promise.reject(error);
});

// 响应拦截器
api.interceptors.response.use((response) => {
  endLoading();
  // 缓存 GET 请求的响应
  if (response.config.method === 'get') {
    const cacheKey = response.config.url + '?' + new URLSearchParams(response.config.params || {}).toString();
    cache[cacheKey] = {
      data: response.data,
      timestamp: Date.now()
    };
  }
  return response;
}, (error) => {
  endLoading();
  // 统一错误处理
  if (error.response) {
    // 服务器返回错误
    console.error('API Error:', error.response.status, error.response.data);
  } else if (error.request) {
    // 请求已发出但没有收到响应
    console.error('API Error: No response received');
  } else {
    // 请求配置出错
    console.error('API Error:', error.message);
  }
  return Promise.reject(error);
});

// 带缓存的 GET 请求
export async function getWithCache<T = any>(url: string, params?: Record<string, any>): Promise<T> {
  const cacheKey = url + '?' + new URLSearchParams(params || {}).toString();
  const cached = cache[cacheKey];
  
  if (cached && (Date.now() - cached.timestamp) < CACHE_DURATION) {
    return cached.data as T;
  }
  
  try {
    const response = await api.get<T>(url, { params });
    return response.data;
  } catch (error) {
    // 重试机制
    let retries = 0;
    while (retries < MAX_RETRIES) {
      retries++;
      try {
        const response = await api.get<T>(url, { params });
        return response.data;
      } catch (retryError) {
        if (retries === MAX_RETRIES) {
          throw retryError;
        }
        // 指数退避策略
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retries)));
      }
    }
    throw error;
  }
}

export { api };
