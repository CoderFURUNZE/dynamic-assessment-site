const KEY = "da_token";
const ROLE_KEY = "da_role";
const EXPIRES_KEY = "da_expires_at";
const USERNAME_KEY = "da_username";

// 输入验证函数
export function validateInput(input: string, type: 'email' | 'password' | 'username'): boolean {
  switch (type) {
    case 'email':
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input);
    case 'password':
      return input.length >= 6;
    case 'username':
      return input.length >= 3 && /^[a-zA-Z0-9_-]+$/.test(input);
    default:
      return false;
  }
}

// 安全的 token 存储
export function setToken(token: string, rememberDays = 0) {
  // 验证 token 格式
  if (!token || typeof token !== 'string' || !token.includes('.')) {
    throw new Error('Invalid token format');
  }
  
  sessionStorage.setItem(KEY, token);
  if (rememberDays > 0) {
    localStorage.setItem(KEY, token);
    localStorage.setItem(EXPIRES_KEY, String(Date.now() + rememberDays * 24 * 60 * 60 * 1000));
  }
  
  // 从 token 中提取并存储角色和用户名
  const role = decodeRoleFromToken(token);
  const username = decodeUsernameFromToken(token);
  if (role) setRole(role);
  if (username) setUsername(username);
}

// 安全的 token 获取
export function getToken(): string | null {
  const token = sessionStorage.getItem(KEY) || localStorage.getItem(KEY);
  if (!token) return null;
  
  // 验证 token 格式
  if (!token.includes('.')) {
    clearToken();
    return null;
  }
  
  // 检查 token 是否过期
  const expires = localStorage.getItem(EXPIRES_KEY);
  if (expires) {
    const ts = Number(expires);
    if (Number.isFinite(ts) && Date.now() > ts) {
      clearToken();
      return null;
    }
  }
  
  return token;
}

// 解码 token 中的角色
function decodeRoleFromToken(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    
    // 安全的 base64 解码
    const payload = safeBase64Decode(parts[1]);
    if (!payload) return null;
    
    const role = payload?.role;
    return typeof role === "string" ? role : null;
  } catch {
    return null;
  }
}

// 解码 token 中的用户名
function decodeUsernameFromToken(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    
    // 安全的 base64 解码
    const payload = safeBase64Decode(parts[1]);
    if (!payload) return null;
    
    const username = payload?.sub;
    return typeof username === "string" ? username : null;
  } catch {
    return null;
  }
}

// 安全的 base64 解码
function safeBase64Decode(base64: string): any {
  try {
    // 处理 URL 安全的 base64
    const padded = base64.replace(/-/g, "+").replace(/_/g, "/") + "===".slice(0, (4 - base64.length % 4) % 4);
    const decoded = atob(padded);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

// 设置角色
export function setRole(role: string) {
  if (!role || typeof role !== 'string') {
    throw new Error('Invalid role');
  }
  sessionStorage.setItem(ROLE_KEY, role);
  if (localStorage.getItem(KEY)) {
    localStorage.setItem(ROLE_KEY, role);
  }
}

// 获取角色
export function getRole(): string | null {
  const token = getToken();
  if (token) {
    const roleFromToken = decodeRoleFromToken(token);
    if (roleFromToken) {
      setRole(roleFromToken);
      return roleFromToken;
    }
  }
  return sessionStorage.getItem(ROLE_KEY) || localStorage.getItem(ROLE_KEY);
}

// 设置用户名
export function setUsername(username: string) {
  if (!username || typeof username !== 'string') {
    throw new Error('Invalid username');
  }
  sessionStorage.setItem(USERNAME_KEY, username);
  if (localStorage.getItem(KEY)) {
    localStorage.setItem(USERNAME_KEY, username);
  }
}

// 获取用户名
export function getUsername(): string | null {
  const token = getToken();
  if (token) {
    const usernameFromToken = decodeUsernameFromToken(token);
    if (usernameFromToken) {
      setUsername(usernameFromToken);
      return usernameFromToken;
    }
  }
  return sessionStorage.getItem(USERNAME_KEY) || localStorage.getItem(USERNAME_KEY);
}

// 清除 token 和相关数据
export function clearToken() {
  const username = sessionStorage.getItem(USERNAME_KEY) || localStorage.getItem(USERNAME_KEY);
  sessionStorage.removeItem(KEY);
  sessionStorage.removeItem(ROLE_KEY);
  sessionStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(EXPIRES_KEY);
  // 清除 last route 数据
  if (username) {
    localStorage.removeItem(`da_last_route_${username}`);
  }
}

// 检查 token 是否有效
export function isTokenValid(): boolean {
  const token = getToken();
  if (!token) return false;
  
  try {
    const parts = token.split(".");
    if (parts.length < 3) return false;
    
    // 验证 token 结构
    const payload = safeBase64Decode(parts[1]);
    if (!payload) return false;
    
    // 检查 token 是否包含必要的字段
    return typeof payload.sub === 'string' && typeof payload.role === 'string';
  } catch {
    return false;
  }
}
