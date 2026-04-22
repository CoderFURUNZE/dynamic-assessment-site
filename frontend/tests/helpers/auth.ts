import { expect, type APIRequestContext, type Page } from "@playwright/test";

const apiBaseURL = process.env.PLAYWRIGHT_API_BASE_URL || "http://127.0.0.1:8000/api";
const teacherUser = process.env.PLAYWRIGHT_TEACHER_USER || "teacher1";
const teacherPass = process.env.PLAYWRIGHT_TEACHER_PASS || "teacher123";
const studentUser = process.env.PLAYWRIGHT_STUDENT_USER || "student1";
const studentPass = process.env.PLAYWRIGHT_STUDENT_PASS || "student123";
const adminUser = process.env.PLAYWRIGHT_ADMIN_USER || "admin";
const adminPass = process.env.PLAYWRIGHT_ADMIN_PASS || "admin123";

type Role = "teacher" | "student" | "admin";

type Session = {
  accessToken: string;
  role: Role;
  username: string;
};

async function login(request: APIRequestContext, endpoint: string, username: string, password: string, role: Role): Promise<Session> {
  const response = await request.post(`${apiBaseURL}${endpoint}`, {
    data: { username, password },
  });
  expect(response.ok(), `login failed for ${username}`).toBeTruthy();
  const data = await response.json();
  return {
    accessToken: String(data.access_token),
    role,
    username,
  };
}

async function applySession(page: Page, session: Session) {
  await page.addInitScript((payload) => {
    const now = Date.now();
    window.localStorage.setItem("da_token", payload.accessToken);
    window.sessionStorage.setItem("da_token", payload.accessToken);
    window.localStorage.setItem("da_role", payload.role);
    window.sessionStorage.setItem("da_role", payload.role);
    window.localStorage.setItem("da_username", payload.username);
    window.sessionStorage.setItem("da_username", payload.username);
    window.localStorage.setItem("da_expires_at", String(now + 7 * 24 * 60 * 60 * 1000));
    window.sessionStorage.setItem("da_auth_grace_until", String(now + 12000));
  }, session);
}

export async function loginAsTeacher(page: Page, request: APIRequestContext) {
  await applySession(page, await login(request, "/auth/login/admin", teacherUser, teacherPass, "teacher"));
}

export async function loginAsStudent(page: Page, request: APIRequestContext) {
  await applySession(page, await login(request, "/auth/login/student", studentUser, studentPass, "student"));
}

export async function loginAsAdmin(page: Page, request: APIRequestContext) {
  await applySession(page, await login(request, "/auth/login/admin", adminUser, adminPass, "admin"));
}
