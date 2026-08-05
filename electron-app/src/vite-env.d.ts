/// <reference types="vite/client" />

declare global {
  interface Window {
    shadowgram: {
      getAppInfo: () => Promise<{ name: string; version: string }>;
      listDocs: () => Promise<{ files: string[] }>;
      readDoc: (payload: { path: string }) => Promise<{ path: string; content: string }>;
      pingServer: (payload: { host: string; port: number; token?: string }) => Promise<{ ok: boolean; status?: number; message?: string }>;
      listTasks: () => Promise<{ tasks: TaskRecord[] }>;
      stopTask: (payload: { taskId: string }) => Promise<{ ok: boolean; message?: string }>;
      clearFinishedTasks: () => Promise<{ ok: boolean; removed?: number }>;
      startAuth: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; message?: string }>;
      submitAuthInput: (payload: { taskId: string; value: string }) => Promise<{ ok: boolean; message?: string }>;
      cancelAuth: (payload: { taskId: string }) => Promise<{ ok: boolean; message?: string }>;
      listSchedules: () => Promise<{ schedules: ScheduleRecord[] }>;
      saveSchedule: (payload: { schedule: ScheduleRecord }) => Promise<{ ok: boolean; schedules: ScheduleRecord[] }>;
      deleteSchedule: (payload: { id: string }) => Promise<{ ok: boolean; schedules: ScheduleRecord[] }>;
      toggleSchedule: (payload: { id: string }) => Promise<{ ok: boolean; schedules: ScheduleRecord[] }>;
      listModules: () => Promise<{ modules: ModuleRecord[] }>;
      startModule: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; message?: string }>;
      startMassSender: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; message?: string }>;
      startNeuro: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; message?: string }>;
      listAccounts: () => Promise<{ accounts: AccountRecord[] }>;
      listAccountTable: () => Promise<{ accounts: Array<Record<string, unknown>> }>;
      bulkSetProxy: (payload: { workdirs: string[]; proxy: string }) => Promise<{ ok: boolean; message?: string }>;
      bulkSetApi: (payload: { workdirs: string[] }) => Promise<{ ok: boolean; message?: string }>;
      bulkLaunch: (payload: { workdirs: string[] }) => Promise<{ ok: boolean; message?: string }>;
      bulkStop: (payload: { workdirs: string[] }) => Promise<{ ok: boolean; message?: string }>;
      bulkCheckProxy: (payload: { workdirs: string[] }) => Promise<{ ok: boolean; message?: string }>;
      bulkClearCache: (payload: { workdirs: string[] }) => Promise<{ ok: boolean; message?: string }>;
      removeAccount: (payload: AccountPayload) => Promise<{ ok: boolean; message?: string }>;
      moveAccount: (payload: AccountPayload & { direction: number }) => Promise<{ ok: boolean; message?: string }>;
      updateAccountMeta: (payload: AccountPayload & { notes?: string; ai_prompt?: string; device_name?: string }) => Promise<{ ok: boolean }>;
      openPath: (payload: AccountPayload) => Promise<{ ok?: boolean } | string>;
      copyPath: (payload: AccountPayload) => Promise<{ ok: boolean }>;
      exportAccountsCsv: () => Promise<{ ok?: boolean; canceled?: boolean; message?: string }>;
      createAccount: (payload: CreateAccountPayload) => Promise<{ accounts: AccountRecord[] }>;
      launchAccount: (payload: AccountPayload) => Promise<{ accounts: AccountRecord[] }>;
      stopAccount: (payload: AccountPayload) => Promise<{ accounts: AccountRecord[] }>;
      checkProxy: (payload: AccountPayload) => Promise<{ ok: boolean }>;
      checkSession: (payload: AccountPayload) => Promise<{ ok: boolean; message: string }>;
      clearCache: (payload: AccountPayload) => Promise<{ ok: boolean; message: string }>;
      getAccountProfile: (payload: AccountPayload) => Promise<{ ok: boolean; account: Record<string, unknown> }>;
      updateAccountProfile: (payload: unknown) => Promise<{ ok: boolean; account?: Record<string, unknown>; message?: string }>;
      generateBio: (payload: AccountPayload) => Promise<{ ok: boolean; bio?: string }>;
      generateApi: (payload: AccountPayload) => Promise<{ ok: boolean; api_id?: string; api_hash?: string }>;
      setAvatar: (payload: unknown) => Promise<{ ok: boolean; path?: string }>;
      setChannelAvatar: (payload: unknown) => Promise<{ ok: boolean; path?: string }>;
      exportSession: (payload: AccountPayload) => Promise<{ ok?: boolean; canceled?: boolean; message?: string }>;
      getNodeSpecs: () => Promise<{ specs: Record<string, NodeSpec> }>;
      openFile: (options: unknown) => Promise<{ canceled: boolean; filePaths: string[] }>;
      openDirectory: () => Promise<{ canceled: boolean; filePaths: string[] }>;
      saveFile: (options: unknown) => Promise<{ canceled: boolean; filePath?: string }>;
      runScenario: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; message?: string }>;
      getScenarioStatus: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; status?: string; logs?: string[]; message?: string }>;
      stopScenario: (payload: unknown) => Promise<{ ok: boolean; taskId?: string; message?: string }>;
      saveScenario: (payload: unknown) => Promise<{ ok: boolean; path?: string }>;
      loadScenario: (payload: unknown) => Promise<{ ok: boolean; graph?: { nodes?: unknown[]; connections?: unknown[] } }>;
      getSettings: () => Promise<{ settings: Record<string, unknown> }>;
      saveSettings: (payload: unknown) => Promise<{ ok: boolean; settings: Record<string, unknown> }>;
      exportPhones: (payload: unknown) => Promise<{ ok?: boolean; canceled?: boolean; message?: string }>;
    };
  }
}

interface AccountRecord { name: string; workdir: string; status: string; proxyStatus: string; [key: string]: unknown }
interface TaskRecord { taskId: string; name: string; status: string; logs: string[]; createdAt?: string | number }
interface ScheduleRecord { id: string; name: string; interval: number; unit: string; enabled?: boolean; scenario?: unknown; [key: string]: unknown }
interface ModuleRecord { name: string; title: string; description?: string; params?: unknown[] }
interface AccountPayload { name?: string; workdir?: string }
interface CreateAccountPayload { name: string; workdir: string; proxy?: string; apiId?: string; apiHash?: string; device?: string }
interface NodeSpec { title: string; category: string; inputs: string[]; outputs: string[]; params: Record<string, { label: string; type: string; default?: unknown; options?: Array<{ value: string; label: string }> }> }

export {};
