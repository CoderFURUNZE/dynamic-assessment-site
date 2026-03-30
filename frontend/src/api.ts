import axios, { isAxiosError } from "axios";
import { ElMessage } from "element-plus";
import { clearToken, getToken, isWithinAuthGracePeriod } from "./token";
import { router } from "./router";
import { startLoading, endLoading } from "./loading";

let handlingUnauthorized = false;

/** 从 axios 配置中取出本次请求携带的 Bearer token（无则空串）；兼容 AxiosHeaders / 普通对象 / 数组 */
function bearerTokenFromRequestConfig(config: unknown): string {
  const c = config as { headers?: Record<string, unknown> & { get?: (name: string) => unknown; toJSON?: () => Record<string, unknown> } } | undefined;
  const h = c?.headers;
  if (!h) return "";
  let raw: unknown;
  if (typeof h.get === "function") {
    raw = h.get("Authorization") ?? h.get("authorization");
  } else {
    raw = (h as Record<string, unknown>).Authorization ?? (h as Record<string, unknown>).authorization;
  }
  if ((raw === undefined || raw === null) && typeof (h as { toJSON?: () => unknown }).toJSON === "function") {
    try {
      const j = (h as { toJSON: () => Record<string, unknown> }).toJSON();
      raw = j.Authorization ?? j.authorization;
    } catch {
      /* ignore */
    }
  }
  let s = "";
  if (typeof raw === "string") s = raw;
  else if (Array.isArray(raw) && raw.length) s = String(raw[0]);
  return s.replace(/^Bearer\s+/i, "").trim();
}

// 缓存机制
const cache: Record<string, { data: any; timestamp: number }> = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5分钟缓存

// 重试机制
const MAX_RETRIES = 3;
const defaultApiBaseUrl =
  import.meta.env.DEV && typeof window !== "undefined"
    ? "/api"
    : typeof window !== "undefined"
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
  const status = error.response?.status;
  if (status === 401) {
    const reqUrl = `${error.config?.baseURL ?? ""}${error.config?.url ?? ""}`;
    const isAuthRequest = /\/auth\/(login|register)/.test(reqUrl);
    const ct = String(error.response?.headers?.["content-type"] ?? "");
    if (ct.includes("text/html")) {
      ElMessage.error("接口返回了网页而非 JSON，常见原因是后端未启动或代理未指向 8000 端口，请检查后再试（此时不应退出登录）");
      return Promise.reject(error);
    }
    if (!isAuthRequest) {
      // 登录成功后，仍可能收到「旧 token」或登录前发出的请求返回 401；若与当前会话 token 不一致，勿清 token / 勿跳转
      const sentToken = bearerTokenFromRequestConfig(error.config);
      const currentToken = getToken() ?? "";
      if (sentToken !== currentToken) {
        return Promise.reject(error);
      }
      // 登录后宽限期内：同一 token 的 401 多为竞态/陈旧响应，不清会话、不弹「重新登录」
      if (sentToken && currentToken && sentToken === currentToken && isWithinAuthGracePeriod()) {
        return Promise.reject(error);
      }
      const path = router.currentRoute.value?.path ?? "";
      if (path !== "/login" && !handlingUnauthorized) {
        handlingUnauthorized = true;
        clearToken();
        const detail = error.response?.data?.detail;
        const friendly =
          detail === "Not authenticated" || detail === "Invalid token" || detail === "User not found"
            ? "登录状态无效或已过期，请重新登录"
            : typeof detail === "string"
              ? detail
              : "登录状态无效或已过期，请重新登录";
        ElMessage.warning(friendly);
        router
          .push({ path: "/login" })
          .catch(() => {})
          .finally(() => {
            setTimeout(() => {
              handlingUnauthorized = false;
            }, 600);
          });
      }
    }
    return Promise.reject(error);
  }
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
    if (isAxiosError(error) && error.response?.status === 401) {
      throw error;
    }
    let retries = 0;
    while (retries < MAX_RETRIES) {
      retries++;
      try {
        const response = await api.get<T>(url, { params });
        return response.data;
      } catch (retryError) {
        if (isAxiosError(retryError) && retryError.response?.status === 401) {
          throw retryError;
        }
        if (retries === MAX_RETRIES) {
          throw retryError;
        }
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retries)));
      }
    }
    throw error;
  }
}

export { api };
