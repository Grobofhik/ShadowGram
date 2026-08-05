import { app, BrowserWindow, ipcMain, dialog, shell, clipboard } from "electron";
import path from "node:path";
import { spawn, ChildProcessWithoutNullStreams } from "node:child_process";
import readline from "node:readline";

let window: BrowserWindow | null = null;
let bridge: ChildProcessWithoutNullStreams | null = null;
let nextId = 1;
const pending = new Map<number, { resolve: (value: unknown) => void; reject: (error: Error) => void }>();

function startBridge() {
  const python = process.platform === "win32" ? "python" : "python3";
  bridge = spawn(python, [path.join(__dirname, "../backend_bridge.py")], { cwd: path.join(__dirname, "../..") });
  const lines = readline.createInterface({ input: bridge.stdout });
  lines.on("line", (line) => {
    try {
      const response = JSON.parse(line) as { id: number; ok: boolean; data?: unknown; error?: string };
      const request = pending.get(response.id);
      if (!request) return;
      pending.delete(response.id);
      response.ok ? request.resolve(response.data) : request.reject(new Error(response.error ?? "Bridge request failed"));
    } catch { /* Ignore malformed backend output. */ }
  });
  bridge.stderr.on("data", (chunk) => console.error(`[python] ${chunk.toString()}`));
}

function callBridge(action: string, payload: unknown = {}) {
  if (!bridge) startBridge();
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    bridge!.stdin.write(`${JSON.stringify({ id, action, payload })}\n`);
  });
}

function createWindow() {
  window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: "#060906",
    title: "ShadowGram",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    void window.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    void window.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(() => {
  ipcMain.handle("app:info", () => ({ name: "ShadowGram", version: app.getVersion() }));
  ipcMain.handle("docs:list", () => callBridge("docs:list"));
  ipcMain.handle("docs:read", (_event, payload) => callBridge("docs:read", payload));
  ipcMain.handle("server:ping", (_event, payload) => callBridge("server:ping", payload));
  ipcMain.handle("tasks:list", () => callBridge("tasks:list"));
  ipcMain.handle("tasks:stop", (_event, payload) => callBridge("tasks:stop", payload));
  ipcMain.handle("tasks:clear-finished", () => callBridge("tasks:clear-finished"));
  ipcMain.handle("auth:start", (_event, payload) => callBridge("auth:start", payload));
  ipcMain.handle("auth:input", (_event, payload) => callBridge("auth:input", payload));
  ipcMain.handle("auth:cancel", (_event, payload) => callBridge("auth:cancel", payload));
  ipcMain.handle("schedules:list", () => callBridge("schedules:list"));
  ipcMain.handle("schedules:save", (_event, payload) => callBridge("schedules:save", payload));
  ipcMain.handle("schedules:delete", (_event, payload) => callBridge("schedules:delete", payload));
  ipcMain.handle("schedules:toggle", (_event, payload) => callBridge("schedules:toggle", payload));
  ipcMain.handle("module:list", () => callBridge("module:list"));
  ipcMain.handle("module:run", (_event, payload) => callBridge("module:run", payload));
  ipcMain.handle("mass-sender:run", (_event, payload) => callBridge("mass-sender:run", payload));
  ipcMain.handle("neuro:run", (_event, payload) => callBridge("neuro:run", payload));
  ipcMain.handle("accounts:list", () => callBridge("accounts:list"));
  ipcMain.handle("accounts:table", () => callBridge("accounts:table"));
  ipcMain.handle("accounts:bulk-proxy", (_event, payload) => callBridge("accounts:bulk-proxy", payload));
  ipcMain.handle("accounts:bulk-api", (_event, payload) => callBridge("accounts:bulk-api", payload));
  ipcMain.handle("accounts:bulk-launch", (_event, payload) => callBridge("accounts:bulk-launch", payload));
  ipcMain.handle("accounts:bulk-stop", (_event, payload) => callBridge("accounts:bulk-stop", payload));
  ipcMain.handle("accounts:bulk-check-proxy", (_event, payload) => callBridge("accounts:bulk-check-proxy", payload));
  ipcMain.handle("accounts:bulk-clear-cache", (_event, payload) => callBridge("accounts:bulk-clear-cache", payload));
  ipcMain.handle("account:remove", (_event, payload) => callBridge("account:remove", payload));
  ipcMain.handle("account:move", (_event, payload) => callBridge("account:move", payload));
  ipcMain.handle("account:update-meta", (_event, payload) => callBridge("account:update-meta", payload));
  ipcMain.handle("account:open-path", (_event, payload) => shell.openPath(String(payload?.workdir ?? "")));
  ipcMain.handle("account:copy-path", (_event, payload) => { clipboard.writeText(String(payload?.workdir ?? "")); return { ok: true }; });
  ipcMain.handle("accounts:export-csv", async () => {
    const result = await dialog.showSaveDialog(window!, { defaultPath: "accounts.csv", filters: [{ name: "CSV", extensions: ["csv"] }] });
    if (result.canceled || !result.filePath) return { canceled: true };
    return callBridge("accounts:export-csv", { outputPath: result.filePath });
  });
  ipcMain.handle("accounts:create", (_event, payload) => callBridge("accounts:create", payload));
  ipcMain.handle("account:launch", (_event, payload) => callBridge("account:launch", payload));
  ipcMain.handle("account:stop", (_event, payload) => callBridge("account:stop", payload));
  ipcMain.handle("account:proxy-check", (_event, payload) => callBridge("account:proxy-check", payload));
  ipcMain.handle("account:session-check", (_event, payload) => callBridge("account:session-check", payload));
  ipcMain.handle("account:clear-cache", (_event, payload) => callBridge("account:clear-cache", payload));
  ipcMain.handle("account:get-profile", (_event, payload) => callBridge("account:get-profile", payload));
  ipcMain.handle("account:update-profile", (_event, payload) => callBridge("account:update-profile", payload));
  ipcMain.handle("account:generate-bio", (_event, payload) => callBridge("account:generate-bio", payload));
  ipcMain.handle("account:generate-api", (_event, payload) => callBridge("account:generate-api", payload));
  ipcMain.handle("account:set-avatar", (_event, payload) => callBridge("account:set-avatar", payload));
  ipcMain.handle("account:set-channel-avatar", (_event, payload) => callBridge("account:set-channel-avatar", payload));
  ipcMain.handle("account:export-session", async (_event, payload) => {
    const result = await dialog.showSaveDialog(window!, { defaultPath: "session_export.zip", filters: [{ name: "ZIP archive", extensions: ["zip"] }] });
    if (result.canceled || !result.filePath) return { canceled: true };
    return callBridge("account:export-session", { ...payload, outputPath: result.filePath });
  });
  ipcMain.handle("node:specs", () => callBridge("node:specs"));
  ipcMain.handle("dialog:open-file", async (_event, options) => dialog.showOpenDialog(window!, options));
  ipcMain.handle("dialog:open-directory", async () => dialog.showOpenDialog(window!, { properties: ["openDirectory"] }));
  ipcMain.handle("dialog:save-file", async (_event, options) => dialog.showSaveDialog(window!, options));
  ipcMain.handle("scenario:run", (_event, payload) => callBridge("scenario:run", payload));
  ipcMain.handle("scenario:status", (_event, payload) => callBridge("scenario:status", payload));
  ipcMain.handle("scenario:stop", (_event, payload) => callBridge("scenario:stop", payload));
  ipcMain.handle("scenario:save", (_event, payload) => callBridge("scenario:save", payload));
  ipcMain.handle("scenario:load", (_event, payload) => callBridge("scenario:load", payload));
  ipcMain.handle("settings:get", () => callBridge("settings:get"));
  ipcMain.handle("settings:save", (_event, payload) => callBridge("settings:save", payload));
  ipcMain.handle("farms:get", () => callBridge("farms:get"));
  ipcMain.handle("farms:switch", (_event, payload) => callBridge("farms:switch", payload));
  ipcMain.handle("farms:create", (_event, payload) => callBridge("farms:create", payload));
  ipcMain.handle("phones:export", async (_event, payload) => {
    const result = await dialog.showSaveDialog(window!, { defaultPath: "phone_numbers.txt", filters: [{ name: "Text files", extensions: ["txt"] }] });
    if (result.canceled || !result.filePath) return { canceled: true };
    return callBridge("phones:export", { ...payload, outputPath: result.filePath });
  });
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  bridge?.kill();
  if (process.platform !== "darwin") app.quit();
});
