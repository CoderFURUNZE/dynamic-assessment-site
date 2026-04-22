# Playwright E2E

## Install browser

```bash
npx playwright install chromium
```

## Run

```bash
npm run e2e
```

## Optional environment variables

```bash
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000/api
PLAYWRIGHT_BASE_URL=http://127.0.0.1:4173
PLAYWRIGHT_TEACHER_USER=teacher1
PLAYWRIGHT_TEACHER_PASS=teacher123
PLAYWRIGHT_STUDENT_USER=student1
PLAYWRIGHT_STUDENT_PASS=student123
PLAYWRIGHT_ADMIN_USER=admin
PLAYWRIGHT_ADMIN_PASS=admin123
```

Default test accounts come from `backend/app/db/bootstrap.py`.
