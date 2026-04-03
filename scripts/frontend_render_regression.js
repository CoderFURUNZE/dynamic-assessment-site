"use strict";

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

function firstExistingPath(candidates) {
  for (const item of candidates) {
    if (item && fs.existsSync(item)) return item;
  }
  return "";
}

function reportPath() {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  return path.resolve(__dirname, "..", "logs", `frontend_render_regression_${stamp}.md`);
}

async function collectMessages(page) {
  const locator = page.locator(".el-message .el-message__content");
  const count = await locator.count();
  const out = [];
  for (let idx = 0; idx < count; idx += 1) {
    out.push((await locator.nth(idx).innerText()).trim());
  }
  return out.filter(Boolean);
}

async function login(page, baseUrl, mode, username, password, expectedPrefix) {
  await page.goto(`${baseUrl}${mode === "staff" ? "/login/staff" : "/login/student"}`, {
    waitUntil: "domcontentloaded",
  });
  await page.locator("input").nth(0).fill(username);
  await page.locator("input").nth(1).fill(password);
  await page.locator(".login-btn").click();
  await page.waitForURL((url) => url.pathname.startsWith(expectedPrefix), { timeout: 15000 });
  await page.waitForTimeout(1800);
}

async function visitRoute(page, baseUrl, scenarioRole, route, findings) {
  const issues = [];
  const onPageError = (err) => issues.push(`pageerror: ${err.message}`);
  const onConsole = (msg) => {
    if (msg.type() === "error") issues.push(`console: ${msg.text()}`);
  };
  const onResponse = (resp) => {
    const url = resp.url();
    if (url.includes("/api/") && resp.status() >= 400) issues.push(`api ${resp.status()}: ${url}`);
  };
  const onRequestFailed = (req) => {
    issues.push(`requestfailed: ${req.method()} ${req.url()} ${req.failure()?.errorText || ""}`);
  };

  page.on("pageerror", onPageError);
  page.on("console", onConsole);
  page.on("response", onResponse);
  page.on("requestfailed", onRequestFailed);
  try {
    await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    const bodyText = (await page.locator("body").innerText()).trim();
    if (bodyText.length < 20) issues.push("body text too short, possible blank render");
    const messages = await collectMessages(page);
    for (const message of messages) issues.push(`ui-message: ${message}`);
  } finally {
    page.off("pageerror", onPageError);
    page.off("console", onConsole);
    page.off("response", onResponse);
    page.off("requestfailed", onRequestFailed);
  }

  for (const issue of issues) {
    findings.push({ role: scenarioRole, route, issue });
  }
}

function writeReport(output, findings) {
  const lines = [
    "# Frontend Render Regression",
    "",
    `- Generated At: ${new Date().toLocaleString("zh-CN", { hour12: false })}`,
    `- Issue Count: ${findings.length}`,
    "",
    "## Details",
    "",
  ];
  if (!findings.length) {
    lines.push("1. [PASS] All checked admin/teacher/student pages rendered without browser or API errors.");
  } else {
    findings.forEach((item, idx) => {
      lines.push(`${idx + 1}. [FAIL] ${item.role} ${item.route}`);
      lines.push(`   - ${item.issue}`);
    });
  }
  fs.writeFileSync(output, `${lines.join("\n")}\n`, "utf8");
}

async function main() {
  const baseUrl = process.env.FRONTEND_BASE_URL || "http://127.0.0.1:5173";
  const browserPath =
    process.env.PLAYWRIGHT_BROWSER_PATH ||
    firstExistingPath([
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    ]);
  if (!browserPath) {
    throw new Error("No Chrome/Edge executable found. Set PLAYWRIGHT_BROWSER_PATH first.");
  }

  const browser = await chromium.launch({ headless: true, executablePath: browserPath });
  const findings = [];
  const output = reportPath();

  const scenarios = [
    {
      role: "admin",
      mode: "staff",
      username: process.env.ADMIN_USER || "admin",
      password: process.env.ADMIN_PASS || "admin123",
      expectedPrefix: "/admin",
      routes: ["/admin/dashboard", "/admin/basic/courses", "/admin/basic/users", "/admin/config", "/admin/audit", "/admin/extensions"],
    },
    {
      role: "teacher",
      mode: "staff",
      username: process.env.TEACHER_USER || "teacher1",
      password: process.env.TEACHER_PASS || "teacher123",
      expectedPrefix: "/teacher",
      routes: ["/teacher/workspace", "/teacher/content", "/teacher/evaluation?tab=imports", "/teacher/students?tab=class", "/teacher/review?tab=enrollment", "/teacher/extensions"],
    },
    {
      role: "student",
      mode: "student",
      username: process.env.STUDENT_USER || "student1",
      password: process.env.STUDENT_PASS || "student123",
      expectedPrefix: "/student",
      routes: ["/student/dashboard", "/student/graph-workspace", "/student/report", "/student/questionnaire", "/student/enroll"],
    },
  ];

  try {
    for (const scenario of scenarios) {
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await login(page, baseUrl, scenario.mode, scenario.username, scenario.password, scenario.expectedPrefix);
        for (const route of scenario.routes) {
          await visitRoute(page, baseUrl, scenario.role, route, findings);
        }
      } catch (err) {
        findings.push({
          role: scenario.role,
          route: "login-or-flow",
          issue: err && err.message ? err.message : String(err),
        });
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  writeReport(output, findings);
  console.log(`[REPORT] ${output}`);
  process.exit(findings.length ? 2 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
