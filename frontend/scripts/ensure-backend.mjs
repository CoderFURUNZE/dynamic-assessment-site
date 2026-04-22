import { existsSync, openSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";
import http from "node:http";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");
const psScript = resolve(rootDir, "scripts", "ensure_backend_server.ps1");
const backendDir = resolve(rootDir, "backend");
const pyPosix = resolve(backendDir, ".venv", "bin", "python");
const openapiUrl = "http://127.0.0.1:8000/api/openapi.json";

function fail(message) {
  console.error(`[ensure-backend] ${message}`);
  process.exit(1);
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: rootDir,
    stdio: "inherit",
    shell: false,
  });

  if (result.error) {
    fail(result.error.message);
  }
  if (result.status !== 0) {
    fail(`command failed: ${command} ${args.join(" ")}`);
  }
}

function wait(ms) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, ms));
}

function isBackendReady() {
  return new Promise((resolvePromise) => {
    const req = http.get(openapiUrl, (res) => {
      res.resume();
      resolvePromise(res.statusCode === 200);
    });
    req.on("error", () => resolvePromise(false));
    req.setTimeout(1500, () => {
      req.destroy();
      resolvePromise(false);
    });
  });
}

async function ensurePosixBackend() {
  if (!existsSync(pyPosix)) {
    fail(`python venv not found: ${pyPosix}`);
  }

  if (await isBackendReady()) {
    return;
  }

  const child = spawn(
    pyPosix,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: backendDir,
      detached: true,
      stdio: ["ignore", openSync(resolve(rootDir, "backend-start.log"), "a"), openSync(resolve(rootDir, "backend-start.log"), "a")],
    },
  );
  child.unref();

  for (let i = 0; i < 30; i += 1) {
    await wait(1000);
    if (await isBackendReady()) {
      return;
    }
  }
  fail(`backend server did not become ready on ${openapiUrl}`);
}

if (process.platform === "win32") {
  if (!existsSync(psScript)) {
    fail(`backend bootstrap script not found: ${psScript}`);
  }
  run("powershell", ["-ExecutionPolicy", "Bypass", "-File", psScript]);
} else {
  await ensurePosixBackend();
}
