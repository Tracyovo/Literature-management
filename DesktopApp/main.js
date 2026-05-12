const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const DEFAULT_PORT = 8000;
let backendProcess = null;
let backendPort = DEFAULT_PORT;

function repoRoot() {
  return path.resolve(__dirname, "..");
}

function resolveFrontendPath() {
  const localFrontend = path.join(__dirname, "Frontend", "index.html");
  const repoFrontend = path.join(repoRoot(), "Frontend", "index.html");
  return fs.existsSync(localFrontend) ? localFrontend : repoFrontend;
}

function resolvePackagedBackendPath() {
  const resourceExe = path.join(
    process.resourcesPath,
    "backend",
    "LiteratureManagerBackend.exe",
  );
  if (fs.existsSync(resourceExe)) {
    return resourceExe;
  }

  const fallbackExe = path.join(
    path.dirname(process.execPath),
    "resources",
    "backend",
    "LiteratureManagerBackend.exe",
  );
  return fallbackExe;
}

function getBackendWorkingDir() {
  if (!app.isPackaged) {
    return path.join(repoRoot(), "Backend");
  }
  const userData = app.getPath("userData");
  fs.mkdirSync(userData, { recursive: true });
  return userData;
}

function getBackendLogPath() {
  return path.join(app.getPath("userData"), "backend-error.log");
}

function logBackendError(message, error) {
  const logLine = `[${new Date().toISOString()}] ${message}`;
  const detail = error ? `\n${String(error.stack || error)}` : "";
  try {
    fs.appendFileSync(getBackendLogPath(), `${logLine}${detail}\n`);
  } catch (logError) {
    // Ignore logging failures.
  }
}

function resolveBackendCommand() {
  if (app.isPackaged) {
    return {
      command: resolvePackagedBackendPath(),
      args: [],
      cwd: getBackendWorkingDir(),
      env: {
        ...process.env,
        LM_HOST: "127.0.0.1",
        LM_PORT: String(backendPort),
      },
    };
  }

  const venvPython = path.join(repoRoot(), ".venv", "Scripts", "python.exe");
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : "python";
  return {
    command: pythonCmd,
    args: [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(backendPort),
    ],
    cwd: getBackendWorkingDir(),
    env: {
      ...process.env,
    },
  };
}

function checkPortInUse(port, host = "127.0.0.1") {
  return new Promise((resolve) => {
    const tester = net
      .createServer()
      .once("error", () => resolve(true))
      .once("listening", () => {
        tester.close(() => resolve(false));
      })
      .listen(port, host);
  });
}

async function findAvailablePort(startPort, attempts) {
  for (let i = 0; i < attempts; i += 1) {
    const candidate = startPort + i;
    const inUse = await checkPortInUse(candidate);
    if (!inUse) {
      return candidate;
    }
  }
  return null;
}

async function startBackend() {
  const defaultInUse = await checkPortInUse(DEFAULT_PORT);
  if (defaultInUse) {
    backendPort = DEFAULT_PORT;
    logBackendError(`Port ${DEFAULT_PORT} is already in use.`, null);
    return;
  }
  const availablePort = await findAvailablePort(DEFAULT_PORT, 20);
  if (!availablePort) {
    logBackendError("No available port found for backend.", null);
    return;
  }
  backendPort = availablePort;
  const { command, args, cwd, env } = resolveBackendCommand();
  backendProcess = spawn(command, args, {
    cwd,
    env,
    stdio: ["ignore", "ignore", "pipe"],
    windowsHide: true,
  });
  backendProcess.on("error", (error) => {
    logBackendError("Backend process failed to start.", error);
  });
  if (backendProcess.stderr) {
    backendProcess.stderr.on("data", (chunk) => {
      logBackendError("Backend stderr output:", chunk.toString("utf8"));
    });
  }
}

function stopBackend() {
  if (!backendProcess) {
    return;
  }
  try {
    backendProcess.kill();
    if (process.platform === "win32" && backendProcess.pid) {
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], {
        stdio: "ignore",
        windowsHide: true,
      });
    }
  } catch (error) {
    // Ignore failures when shutting down.
  }
  backendProcess = null;
}

function waitForBackend(url, timeoutMs) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode < 500) {
          resolve();
        } else {
          retry();
        }
      });
      req.on("error", retry);
      req.setTimeout(1500, () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error("Backend did not start in time."));
        return;
      }
      setTimeout(attempt, 300);
    };

    attempt();
  });
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1200,
    height: 820,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const apiBase = `http://127.0.0.1:${backendPort}`;
  await window.loadFile(resolveFrontendPath(), {
    query: { apiBase },
  });
}

app.whenReady().then(async () => {
  await startBackend();
  try {
    await waitForBackend(`http://127.0.0.1:${backendPort}/`, 15000);
  } catch (error) {
    // Continue and let the UI show errors if backend is unavailable.
  }
  await createWindow();
});

app.on("before-quit", stopBackend);
app.on("quit", () => {
  stopBackend();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
