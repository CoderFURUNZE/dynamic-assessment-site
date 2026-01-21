const KEY = "da_token";
const ROLE_KEY = "da_role";
const EXPIRES_KEY = "da_expires_at";

export function getToken(): string | null {
  const token = sessionStorage.getItem(KEY) || localStorage.getItem(KEY);
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

export function setToken(token: string, rememberDays = 0) {
  sessionStorage.setItem(KEY, token);
  if (rememberDays > 0) {
    localStorage.setItem(KEY, token);
    localStorage.setItem(EXPIRES_KEY, String(Date.now() + rememberDays * 24 * 60 * 60 * 1000));
  }
}

function decodeRoleFromToken(token: string | null): string | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    const role = payload?.role;
    return typeof role === "string" ? role : null;
  } catch {
    return null;
  }
}

export function setRole(role: string) {
  sessionStorage.setItem(ROLE_KEY, role);
  if (localStorage.getItem(KEY)) {
    localStorage.setItem(ROLE_KEY, role);
  }
}

export function getRole(): string | null {
  const roleFromToken = decodeRoleFromToken(getToken());
  if (roleFromToken) {
    setRole(roleFromToken);
    return roleFromToken;
  }
  return sessionStorage.getItem(ROLE_KEY) || localStorage.getItem(ROLE_KEY);
}

export function getUsername(): string | null {
  const token = getToken();
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    const username = payload?.sub;
    return typeof username === "string" ? username : null;
  } catch {
    return null;
  }
}

export function clearToken() {
  sessionStorage.removeItem(KEY);
  sessionStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(EXPIRES_KEY);
}
