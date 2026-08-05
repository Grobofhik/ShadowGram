import React, { useState, useEffect } from "react";
import { Bot, Play, RefreshCw, SlidersHorizontal } from "lucide-react";
import { ModuleRecord, AccountRecord } from "../types";

interface ModulesPageProps {
  accounts: AccountRecord[];
  notify: (msg: string) => void;
}

export const ModulesPage: React.FC<ModulesPageProps> = ({ accounts: items, notify }) => {
  const [modules, setModules] = useState<ModuleRecord[]>([]);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [params, setParams] = useState<Record<string, any>>({});
  const [logs, setLogs] = useState<string>("MODULE_RUNNER_READY...");
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);

  useEffect(() => {
    void (window as any).shadowgram
      ?.listModules()
      .then((response: any) => {
        if (response?.modules) {
          setModules(response.modules);
          if (response.modules.length > 0) {
            setSelectedModule(response.modules[0].name);
          }
        }
      })
      .catch(() => undefined);

    setSelectedAccounts(items.map((acc) => acc.name || (acc.workdir as string)));
  }, [items]);

  const activeModule = modules.find((m) => m.name === selectedModule) || modules[0];

  const handleParamChange = (key: string, value: any) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const runModule = async () => {
    if (!activeModule) return;
    const selectedAccObjects = items.filter((acc) =>
      selectedAccounts.includes(acc.name || (acc.workdir as string))
    );

    if (selectedAccObjects.length === 0) {
      notify("Выберите хотя бы один аккаунт для запуска модуля!");
      return;
    }

    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.runModule({
      module: activeModule.name,
      accounts: selectedAccObjects,
      params,
    });

    if (res?.ok && res.taskId) {
      setRunningTaskId(res.taskId);
      notify(`Модуль '${activeModule.title}' запущен!`);

      const poll = async () => {
        const statusRes = await shadowgram?.listTasks();
        const currentTask = (statusRes?.tasks || []).find((t: any) => t.taskId === res.taskId);
        if (currentTask?.logs) {
          setLogs(currentTask.logs.join("\n"));
        }
        if (currentTask?.status === "running") {
          setTimeout(poll, 1000);
        } else {
          setRunningTaskId(null);
        }
      };
      void poll();
    } else {
      notify(res?.message || "Ошибка запуска модуля");
    }
  };

  const stopModule = async () => {
    if (!runningTaskId) return;
    await (window as any).shadowgram?.stopTask({ taskId: runningTaskId });
    notify("Остановка модуля запрошена");
  };

  return (
    <div className="page modules-page">
      <section className="page-hero">
        <div>
          <div className="hero-kicker">
            <Bot size={15} /> AUTOMATION MODULES
          </div>
          <h2>Модули управления</h2>
          <p>
            Пакетный запуск авто-комментинга, прогрева, смены аватарок, био и реакторов.
          </p>
        </div>
      </section>

      <div className="modules-layout">
        {/* Sidebar module picker */}
        <aside className="panel module-picker">
          <div className="panel-kicker">ДОСТУПНЫЕ МОДУЛИ ({modules.length})</div>
          <div className="module-list" style={{ marginTop: "10px", display: "grid", gap: "6px" }}>
            {modules.map((m) => (
              <button
                key={m.name}
                className={selectedModule === m.name ? "module-item active" : "module-item"}
                onClick={() => {
                  setSelectedModule(m.name);
                  setParams({});
                }}
              >
                <Bot size={15} />
                <span>{m.title}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* Main configuration workspace */}
        <section className="panel module-config">
          {activeModule ? (
            <>
              <div className="panel-head">
                <div>
                  <div className="panel-kicker">{activeModule.name.toUpperCase()}</div>
                  <h3>{activeModule.title}</h3>
                  <p className="modal-copy" style={{ margin: "5px 0 0" }}>
                    {activeModule.description || "Описание отсутствует"}
                  </p>
                </div>

                {runningTaskId ? (
                  <button className="danger-btn" onClick={stopModule}>
                    Остановить
                  </button>
                ) : (
                  <button className="primary-btn" onClick={runModule}>
                    <Play size={15} /> Запустить модуль
                  </button>
                )}
              </div>

              {/* Dynamic Params Forms */}
              {activeModule.params && activeModule.params.length > 0 && (
                <div style={{ margin: "18px 0" }}>
                  <div className="panel-kicker">ПАРАМЕТРЫ МОДУЛЯ</div>
                  <div className="form-grid">
                    {activeModule.params.map((p: any) => (
                      <label className="form-field" key={p.name}>
                        {p.label.toUpperCase()}
                        {p.type === "textarea" ? (
                          <textarea
                            value={params[p.name] ?? String(p.default ?? "")}
                            onChange={(e) => handleParamChange(p.name, e.target.value)}
                          />
                        ) : p.type === "select" ? (
                          <select
                            value={params[p.name] ?? String(p.default ?? "")}
                            onChange={(e) => handleParamChange(p.name, e.target.value)}
                          >
                            {(p.options || []).map((opt: any) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type={p.type === "int" ? "number" : "text"}
                            value={params[p.name] ?? String(p.default ?? "")}
                            onChange={(e) => handleParamChange(p.name, e.target.value)}
                          />
                        )}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Accounts Selector */}
              <div style={{ margin: "18px 0" }}>
                <div className="panel-kicker">
                  ЦЕЛЕВЫЕ АККАУНТЫ ({selectedAccounts.length} / {items.length})
                </div>
                <div className="account-check-list">
                  {items.map((acc) => {
                    const accId = acc.name || (acc.workdir as string);
                    const checked = selectedAccounts.includes(accId);
                    return (
                      <label key={accId}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            setSelectedAccounts((prev) =>
                              checked ? prev.filter((id) => id !== accId) : [...prev, accId]
                            )
                          }
                        />
                        {accId} <span>{acc.status}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Console log */}
              <div style={{ marginTop: "18px" }}>
                <div className="panel-kicker">LIVE ЛОГ ВЫПОЛНЕНИЯ</div>
                <pre className="module-log">{logs}</pre>
              </div>
            </>
          ) : (
            <div className="table-empty">Загрузка модулей...</div>
          )}
        </section>
      </div>
    </div>
  );
};
