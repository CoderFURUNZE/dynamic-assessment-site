import { expect, test, type Page } from "@playwright/test";
import { loginAsAdmin, loginAsStudent, loginAsTeacher } from "./helpers/auth";

async function expectTab(page: { url: () => string }, value: string) {
  await expect.poll(() => new URL(page.url()).searchParams.get("tab")).toBe(value);
}

function monitorClientErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => {
    errors.push(`pageerror: ${error.message}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(`console: ${message.text()}`);
    }
  });
  return errors;
}

test.describe("public shell", () => {
  test("start page and login page render", async ({ page }) => {
    const errors = monitorClientErrors(page);
    await page.goto("/start");
    await expect(page).toHaveURL(/\/start$/);
    await expect(page.locator("button.start-brand")).toBeVisible();
    await expect(page.getByRole("heading", { name: /动态评价模型研究及应用/ })).toBeVisible();
    await page.getByRole("button", { name: "学生登录" }).click();

    await expect(page).toHaveURL(/\/login\/student$/);
    await expect(page.locator("form.login-form")).toBeVisible();
    await expect(page.getByRole("heading", { name: "学生登录" })).toBeVisible();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    expect(errors).toEqual([]);
  });
});

test.describe("teacher workspace smoke", () => {
  test.beforeEach(async ({ page, request }) => {
    await loginAsTeacher(page, request);
  });

  test("teacher can open evaluation, imports, students and review", async ({ page }) => {
    const errors = monitorClientErrors(page);
    await page.goto("/teacher/workspace");
    await expect(page).toHaveURL(/\/teacher\/workspace/);
    await expect(page.locator(".student-shell__header")).toBeVisible();

    await page.getByRole("button", { name: "阶段评价" }).click();
    await page.getByRole("button", { name: "数据导入" }).click();
    await page.waitForTimeout(800);
    await expectTab(page, "imports");
    await expect(page.getByRole("heading", { name: "数据导入" })).toBeVisible();

    await page.getByRole("button", { name: "结果查看" }).click();
    await page.waitForTimeout(800);
    await expectTab(page, "behavior");
    await expect(page.locator("h1").filter({ hasText: "结果查看" })).toBeVisible();

    await page.goto("/teacher/students?tab=detail");
    await page.waitForTimeout(800);
    await expectTab(page, "detail");
    await expect(page.getByRole("heading", { name: "学生详情" })).toBeVisible();

    await page.goto("/teacher/students?tab=results");
    await page.waitForTimeout(800);
    await expectTab(page, "results");
    await expect(page.locator("h1").filter({ hasText: "画像结果" })).toBeVisible();

    await page.goto("/teacher/review?tab=enrollment");
    await expectTab(page, "enrollment");
    await expect(page.getByRole("heading", { name: "审核与评分" })).toBeVisible();

    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    expect(errors).toEqual([]);
  });
});

test.describe("student workspace smoke", () => {
  test.beforeEach(async ({ page, request }) => {
    await loginAsStudent(page, request);
  });

  test("student can open main routes", async ({ page }) => {
    const errors = monitorClientErrors(page);
    await page.goto("/student/dashboard");
    await expect(page).toHaveURL(/\/student\/dashboard/);
    await expect(page.locator(".student-shell__header")).toBeVisible();

    await page.getByRole("button", { name: "学习任务" }).click();
    await page.getByRole("button", { name: "学习报告" }).click();
    await expect(page).toHaveURL(/\/student\/report/);
    await expect(page.getByRole("button", { name: /返回学习中心/ })).toBeVisible();

    await page.getByRole("button", { name: "学习总览" }).click();
    await page.getByRole("button", { name: "知识图谱" }).click();
    await expect(page).toHaveURL(/\/student\/graph-workspace/);
    await expect(page.locator(".graph-page")).toBeVisible();
    expect(errors).toEqual([]);
  });
});

test.describe("admin workspace smoke", () => {
  test.beforeEach(async ({ page, request }) => {
    await loginAsAdmin(page, request);
  });

  test("admin can open dashboard and core management pages", async ({ page }) => {
    const errors = monitorClientErrors(page);
    await page.goto("/admin/dashboard");
    await expect(page).toHaveURL(/\/admin\/dashboard/);
    await expect(page.getByRole("heading", { name: "后台总览" })).toBeVisible();

    await page.getByRole("button", { name: "基础管理" }).click();
    await page.getByRole("button", { name: "课程管理" }).click();
    await expect(page).toHaveURL(/\/admin\/basic\/courses/);
    await expect(page.locator(".admin-courses-page")).toBeVisible();
    await expect(page.getByText("课程管理").first()).toBeVisible();

    await page.getByRole("button", { name: "用户管理" }).click();
    await expect(page).toHaveURL(/\/admin\/basic\/users/);
    await expect(page.locator(".admin-users-page")).toBeVisible();
    await expect(page.getByText("用户管理").first()).toBeVisible();

    await page.getByRole("button", { name: "评价配置" }).click();
    await page.getByRole("button", { name: "维度指标" }).click();
    await expect(page).toHaveURL(/\/admin\/evaluation\/dimensions/);
    await expect(page.locator(".admin-dimensions-page")).toBeVisible();
    await expect(page.getByText("维度与指标").first()).toBeVisible();
    expect(errors).toEqual([]);
  });
});
