import React, { useEffect, useState, useMemo } from "react";
import {
  SquareTerminal,
  ChevronRight,
  Activity,
  CircleHelp,
  MoreHorizontal,
  Gauge,
  Users,
  LayoutGrid,
  Server,
  Bot,
  BrainCircuit,
  Send,
  Sparkles,
  Workflow,
  Box,
  FileText,
  Settings,
  RefreshCw,
  Plus,
  ShieldCheck,
  Zap,
  Network,
  Play,
  SlidersHorizontal,
  Search,
  X,
} from "lucide-react";
import { Page, AccountRecord, TaskRecord } from "./types";
import { NodeEditorPage } from "./pages/NodeEditorPage";
import { ModulesPage } from "./pages/ModulesPage";
import { MassSenderPage } from "./pages/MassSenderPage";
import { NeuroPage } from "./pages/NeuroPage";
import { ServicesPage } from "./pages/ServicesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TablePage } from "./pages/TablePage";
import { ServerPage } from "./pages/ServerPage";
import { DocumentationPage } from "./pages/DocumentationPage";

const navItems = [
  { label: "Accounts", icon: Users },
  { label: "Create", icon: Plus },
  { label: "Dashboard", icon: Gauge },
  { label: "Table", icon: LayoutGrid },
  { label: "Server", icon: Server },
  { label: "Modules", icon: Bot },
  { label: "Neuro", icon: BrainCircuit },
  { label: "Mass Sender", icon: Send },
  { label: "AI Assistant", icon: Sparkles },
  { label: "Node Editor", icon: Workflow },
  { label: "Services", icon: Box },
  { label: "Documentation", icon: FileText },
  { label: "Settings", icon: Settings },
] as const;

export function App() {
  const [page, setPage] = useState<Page>("Dashboard");
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  const [accounts, setAccounts] = useState<AccountRecord[]>([]);
  const [activeFarm, setActiveFarm] = useState<string>("main");

  const notify = (msg: string) => {
    setNotice(msg);
    setTimeout(() => setNotice(""), 2500);
  };

  const loadAccounts = async () => {
    try {
      const res = await (window as any).shadowgram?.listAccounts();
      if (res?.accounts) {
        setAccounts(res.accounts);
      }
    } catch {
      // Ignored
    }
  };

  const loadFarmInfo = async () => {
    try {
      const res = await (window as any).shadowgram?.getFarms();
      if (res?.active) {
        setActiveFarm(res.active);
      }
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    void loadAccounts();
    void loadFarmInfo();
  }, []);

  const handleFarmChanged = () => {
    void loadAccounts();
    void loadFarmInfo();
    notify("Данные обновлены под новую ферму!");
  };

  const visibleAccounts = useMemo(() => {
    return accounts.filter((acc) => {
      const q = query.toLowerCase();
      return (
        acc.name.toLowerCase().includes(q) ||
        acc.workdir.toLowerCase().includes(q) ||
        (acc.device_name || "").toLowerCase().includes(q)
      );
    });
  }, [accounts, query]);

  return (
    <div className="app-shell">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <SquareTerminal size={19} />
          </div>
          <div>
            <b>SHADOWGRAM</b>
            <span>CONTROL CENTER</span>
          </div>
        </div>

        <div className="farm-chip">
          <span className="status-dot" /> FARM / {activeFarm.toUpperCase()}{" "}
          <ChevronRight size={14} />
        </div>

        <div className="nav-label">WORKSPACE</div>
        <nav>
          {navItems.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={page === label ? "nav-item active" : "nav-item"}
            onClick={() => {
              setPage(label as Page);
            }}
            >
              <Icon size={17} />
              <span>{label}</span>
              {page === label && <i />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-card">
            <div className="system-head">
              <span>System health</span>
              <span className="health">99%</span>
            </div>
            <div className="health-bar">
              <i />
            </div>
            <small>
              <Activity size={12} /> Local engine active
            </small>
          </div>
          <div className="user-row">
            <div className="avatar">SG</div>
            <div>
              <b>operator</b>
              <span>active farm</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main App Canvas */}
      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="eyebrow">WORKSPACE / {page.toUpperCase()}</div>
            <h1>{page === "Dashboard" ? "Operations overview" : page}</h1>
          </div>
          <div className="top-actions">
            <div className="live-pill">
              <span className="status-dot" /> ENGINE ONLINE
            </div>
            <button
              className="icon-btn"
              title="Refresh Workspace"
              onClick={() => {
                void loadAccounts();
                notify("Списки обновлены!");
              }}
            >
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        {page === "Node Editor" && (
          <NodeEditorPage accounts={accounts} notify={notify} />
        )}
        {page === "Modules" && (
          <ModulesPage accounts={accounts} notify={notify} />
        )}
        {page === "Mass Sender" && (
          <MassSenderPage accounts={accounts} notify={notify} />
        )}
        {page === "Neuro" && <NeuroPage accounts={accounts} notify={notify} />}
        {page === "Services" && (
          <ServicesPage accounts={accounts} notify={notify} />
        )}
        {page === "Settings" && (
          <SettingsPage notify={notify} onFarmChanged={handleFarmChanged} />
        )}
        {page === "Table" && <TablePage notify={notify} />}
        {page === "Server" && <ServerPage notify={notify} />}
        {page === "Documentation" && <DocumentationPage notify={notify} />}
        {page === "AI Assistant" && <TaskConsolePage notify={notify} />}

        {/* Fallback rendering for standard components */}
        {page === "Dashboard" && (
          <Dashboard
            accounts={visibleAccounts}
            query={query}
            setQuery={setQuery}
          />
        )}
        {page === "Accounts" && (
          <AccountsView accounts={visibleAccounts} notify={notify} onChanged={loadAccounts} />
        )}
        {page === "Create" && <CreateProfilePage notify={notify} onCreated={async () => { await loadAccounts(); setPage("Accounts"); }} />}
      </main>

      {notice && (
        <div className="toast">
          <ShieldCheck size={16} /> {notice}
        </div>
      )}
    </div>
  );
}

function Dashboard({
  accounts,
  query,
  setQuery,
}: {
  accounts: AccountRecord[];
  query: string;
  setQuery: (v: string) => void;
}) {
  return (
    <div className="page">
      <section className="hero">
        <div>
          <div className="hero-kicker">
            <Zap size={15} /> LIVE TELEGRAM FARM
          </div>
          <h2>
            Good evening, operator<span>.</span>
          </h2>
          <p>Мониторинг аккаунтов, сессий и задач управления ShadowGram.</p>
        </div>
      </section>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon green">
            <Users size={18} />
          </div>
          <span>Всего аккаунтов</span>
          <strong>{accounts.length}</strong>
          <small className="trend">В текущей ферме</small>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel accounts-panel">
          <div className="panel-head">
            <div>
              <div className="panel-kicker">СЕССИИ</div>
              <h3>Аккаунты фермы</h3>
            </div>
          </div>
          <div className="toolbar">
            <div className="search">
              <Search size={16} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск аккаунта..."
              />
            </div>
          </div>
          <div className="account-list">
            {accounts.map((acc) => (
              <div className="account-row" key={acc.name || acc.workdir}>
                <div className="account-avatar">
                  {acc.name.slice(0, 2).toUpperCase()}
                </div>
                <div className="account-info">
                  <b>{acc.name}</b>
                  <span>{acc.workdir}</span>
                </div>
                <span
                  className={
                    acc.status === "Running" ? "badge success" : "badge muted"
                  }
                >
                  {acc.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function AccountsView({
  accounts,
  notify,
  onChanged,
}: {
  accounts: AccountRecord[];
  notify: (msg: string) => void;
  onChanged: () => Promise<void>;
}) {
  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <div className="hero-kicker">
            <Users size={15} /> ACCOUNT MANAGEMENT
          </div>
          <h2>Список профилей Telegram</h2>
        </div>
      </section>
      <div className="full-account-list">
        {accounts.map((acc) => (
            <article className="full-account-row" key={acc.name || acc.workdir}>
            <div className="account-avatar large">
              {acc.name.slice(0, 2).toUpperCase()}
            </div>
            <div className="full-account-main">
              <div className="full-account-title">
                <h3>{acc.name}</h3>
                <span
                  className={
                    acc.status === "Running" ? "badge success" : "badge muted"
                  }
                >
                  {acc.status}
                </span>
              </div>
              <span className="account-path">{acc.workdir}</span>
              <div className="account-actions">
                <button className="tool-btn" onClick={async () => { const r = await (window as any).shadowgram?.launchAccount({ workdir: acc.workdir }); notify(r?.ok ? "Аккаунт запущен" : "Не удалось запустить аккаунт"); await onChanged(); }}>Запустить</button>
                <button className="tool-btn" onClick={async () => { const r = await (window as any).shadowgram?.stopAccount({ workdir: acc.workdir }); notify(r?.ok ? "Аккаунт остановлен" : "Не удалось остановить аккаунт"); await onChanged(); }}>Остановить</button>
                <button className="tool-btn" onClick={async () => { const r = await (window as any).shadowgram?.checkProxy({ workdir: acc.workdir }); notify(r?.ok ? "Прокси доступен" : "Прокси недоступен"); }}>Проверить прокси</button>
                <button className="tool-btn" onClick={async () => { const r = await (window as any).shadowgram?.clearCache({ workdir: acc.workdir }); notify(r?.message || "Кэш очищен"); }}>Очистить кэш</button>
                <button className="tool-btn danger" onClick={async () => { const r = await (window as any).shadowgram?.removeAccount({ workdir: acc.workdir }); notify(r?.message || "Аккаунт удалён"); await onChanged(); }}>Удалить</button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function CreateProfilePage({ notify, onCreated }: { notify: (msg: string) => void; onCreated: () => Promise<void> }) {
  const [name, setName] = useState(""); const [workdir, setWorkdir] = useState(""); const [proxy, setProxy] = useState(""); const [device, setDevice] = useState(""); const [apiId, setApiId] = useState(""); const [apiHash, setApiHash] = useState("");
  const create = async () => { if (!name.trim() || !workdir.trim()) { notify("Укажите имя и папку профиля"); return; } const r = await (window as any).shadowgram?.createAccount({ name, workdir, proxy, device, apiId, apiHash }); if (r?.ok) { notify("Профиль создан"); await onCreated(); } else notify("Не удалось создать профиль"); };
  return <div className="page"><section className="page-hero"><div><div className="hero-kicker"><Plus size={15} /> PROFILE CREATOR</div><h2>Создание профиля</h2></div></section><div className="panel form-panel"><label className="form-field">ИМЯ<input value={name} onChange={(e) => setName(e.target.value)} /></label><label className="form-field">РАБОЧАЯ ПАПКА<input value={workdir} onChange={(e) => setWorkdir(e.target.value)} /></label><div className="form-grid"><label className="form-field">PROXY<input value={proxy} onChange={(e) => setProxy(e.target.value)} /></label><label className="form-field">DEVICE<input value={device} onChange={(e) => setDevice(e.target.value)} /></label></div><div className="form-grid"><label className="form-field">API ID<input value={apiId} onChange={(e) => setApiId(e.target.value)} /></label><label className="form-field">API HASH<input value={apiHash} onChange={(e) => setApiHash(e.target.value)} /></label></div><button className="primary-btn" onClick={() => void create()}>Создать профиль</button></div></div>;
}

function TaskConsolePage({ notify }: { notify: (msg: string) => void }) {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const refresh = async () => {
    const result = await (window as any).shadowgram?.listTasks();
    setTasks(result?.tasks || []);
  };
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="page">
      <section className="page-hero"><div><div className="hero-kicker"><Sparkles size={15} /> AI ASSISTANT</div><h2>Активные задачи и журнал выполнения</h2></div></section>
      <div className="panel task-console">
        <div className="panel-head"><h3>Задачи</h3><button className="tool-btn" onClick={async () => { await (window as any).shadowgram?.clearFinishedTasks(); await refresh(); notify("Завершённые задачи очищены"); }}>Очистить завершённые</button></div>
        {tasks.length === 0 ? <p className="muted-copy">Активных задач нет.</p> : tasks.map((task) => <div className="task-row" key={task.taskId}><div><b>{task.name}</b><span>{task.stage || task.status}</span></div><button className="tool-btn" disabled={["completed", "failed", "stopped", "cancelled"].includes(task.status)} onClick={async () => { await (window as any).shadowgram?.stopTask({ taskId: task.taskId }); notify("Остановка задачи запрошена"); await refresh(); }}>Остановить</button></div>)}
      </div>
    </div>
  );
}
