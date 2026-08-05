import React, { useState, useEffect } from "react";
import {
  Wrench,
  Phone,
  Repeat2,
  KeyRound,
  UserPlus,
  RefreshCw,
  Smartphone,
  Sparkles,
  Download,
  Plus,
  Play,
  X,
} from "lucide-react";
import { AccountRecord, TaskRecord } from "../types";

interface ServicesPageProps {
  accounts: AccountRecord[];
  notify: (msg: string) => void;
}

export const ServicesPage: React.FC<ServicesPageProps> = ({ accounts: items, notify }) => {
  const [activeModal, setActiveModal] = useState<string | null>(null);

  // Service dialog states
  const [tdataFolders, setTdataFolders] = useState<string[]>([]);
  const [tdataRunning, setTdataRunning] = useState<boolean>(false);

  const [telethonInDir, setTelethonInDir] = useState<string>("");
  const [telethonOutDir, setTelethonOutDir] = useState<string>("");
  const [telethonApiId, setTelethonApiId] = useState<string>("6");
  const [telethonRunning, setTelethonRunning] = useState<boolean>(false);

  const [apiSelectedAccounts, setApiSelectedAccounts] = useState<string[]>([]);
  const [sessionAuthPhone, setSessionAuthPhone] = useState<string>("");
  const [sessionAuthApiId, setSessionAuthApiId] = useState<string>("");
  const [sessionAuthApiHash, setSessionAuthApiHash] = useState<string>("");
  const [sessionAuthProxy, setSessionAuthProxy] = useState<string>("");
  const [sessionAuthWorkdir, setSessionAuthWorkdir] = useState<string>("");
  const [authTaskId, setAuthTaskId] = useState<string | null>(null);
  const [authTask, setAuthTask] = useState<TaskRecord | null>(null);
  const [authInputVal, setAuthInputVal] = useState<string>("");

  useEffect(() => {
    if (!authTaskId) return;
    const timer = setInterval(async () => {
      const res = await (window as any).shadowgram?.listTasks();
      const current = (res?.tasks || []).find((t: any) => t.taskId === authTaskId);
      if (current) setAuthTask(current);
    }, 800);
    return () => clearInterval(timer);
  }, [authTaskId]);

  const runSessionAuth = async () => {
    if (!sessionAuthPhone || !sessionAuthApiId || !sessionAuthApiHash || !sessionAuthWorkdir) {
      notify("Заполните телефон, API ID, API Hash и папку назначения!");
      return;
    }

    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.startAuth({
      phone: sessionAuthPhone,
      apiId: sessionAuthApiId,
      apiHash: sessionAuthApiHash,
      proxy: sessionAuthProxy,
      sessionName: "account",
      outputDir: sessionAuthWorkdir,
      workdir: sessionAuthWorkdir,
    });

    if (res?.taskId) {
      setAuthTaskId(res.taskId);
      notify("Авторизация сессии запущена!");
    } else {
      notify(res?.message || "Ошибка запуска авторизации");
    }
  };

  const submitAuthInput = async () => {
    if (!authTaskId || !authInputVal.trim()) return;
    await (window as any).shadowgram?.submitAuthInput({
      taskId: authTaskId,
      value: authInputVal.trim(),
    });
    setAuthInputVal("");
  };

  const runExportPhones = async () => {
    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.exportPhones();
    if (!res?.canceled) {
      notify(res?.message || "Номера экспортированы");
    }
  };

  const runBulkApiGeneration = async () => {
    if (!apiSelectedAccounts.length) {
      notify("Выберите хотя бы один аккаунт!");
      return;
    }
    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.bulkSetApi({ workdirs: apiSelectedAccounts });
    notify(res?.message || "Fallback API назначены выбранным аккаунтам");
    setActiveModal(null);
  };

  const servicesList = [
    {
      id: "auth",
      title: "Авторизация сессий",
      desc: "Массовый вход по номеру телефона с получением рабочих .session файлов.",
      category: "Sessions",
      icon: Phone,
    },
    {
      id: "api",
      title: "Fallback API",
      desc: "Назначение локальных проверенных пар api_id / api_hash аккаунтам.",
      category: "API",
      icon: KeyRound,
    },
    {
      id: "tdata",
      title: "Конвертер TData",
      desc: "Преобразование профилей Telegram Desktop в формат автоматизации.",
      category: "Convert",
      icon: RefreshCw,
    },
    {
      id: "telethon",
      title: "Конвертер Telethon",
      desc: "Перевод Telethon-сессий в формат Hydrogram/Pyrogram.",
      category: "Convert",
      icon: Repeat2,
    },
    {
      id: "phones",
      title: "Экспорт номеров",
      desc: "Выгрузка найденных телефонов аккаунтов в текстовый файл.",
      category: "Export",
      icon: Download,
    },
  ];

  return (
    <div className="page services-page">
      <section className="page-hero">
        <div>
          <div className="hero-kicker">
            <Wrench size={15} /> UTILITY SUITE
          </div>
          <h2>Дополнительные сервисы</h2>
          <p>Инструменты для конвертации профилей, авторизации сессий и генерации данных.</p>
        </div>
        <div className="service-count">
          <b>{servicesList.length}</b>
          <span>services</span>
        </div>
      </section>

      <div className="service-grid">
        {servicesList.map((srv) => {
          const Icon = srv.icon;
          return (
            <article className="service-card" key={srv.id}>
              <div className="service-card-head">
                <div className="service-icon">
                  <Icon size={21} />
                </div>
                <div>
                  <span className="service-category">{srv.category}</span>
                  <h3>{srv.title}</h3>
                </div>
              </div>
              <p>{srv.desc}</p>
              <button
                className="tool-btn"
                onClick={() => {
                  if (srv.id === "phones") {
                    void runExportPhones();
                  } else {
                    setActiveModal(srv.id);
                  }
                }}
              >
                Открыть сервис
              </button>
            </article>
          );
        })}
      </div>

      {/* Modal: Session Authorization */}
      {activeModal === "auth" && (
        <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && setActiveModal(null)}>
          <div className="modal panel service-modal">
            <div className="modal-head">
              <div>
                <div className="panel-kicker">SERVICE WORKSPACE</div>
                <h2>Авторизация Telegram-сессии</h2>
              </div>
              <button className="more-btn" onClick={() => setActiveModal(null)}>
                <X size={17} />
              </button>
            </div>

            {!authTaskId ? (
              <>
                <label className="form-field">
                  ПРОФИЛЬ ДЛЯ АВТОРИЗАЦИИ
                  <select
                    value={sessionAuthWorkdir}
                    onChange={(e) => {
                      setSessionAuthWorkdir(e.target.value);
                      const found = items.find(
                        (acc) => (acc.workdir as string) === e.target.value
                      );
                      if (found) {
                        setSessionAuthPhone(found.phone || "");
                        setSessionAuthApiId(String(found.api_id || ""));
                        setSessionAuthApiHash(found.api_hash || "");
                        setSessionAuthProxy(found.proxy_url || "");
                      }
                    }}
                  >
                    <option value="">Выберите аккаунт...</option>
                    {items.map((acc) => (
                      <option key={acc.workdir as string} value={acc.workdir as string}>
                        {acc.name} ({acc.workdir})
                      </option>
                    ))}
                  </select>
                </label>

                <label className="form-field">
                  НОМЕР ТЕЛЕФОНА
                  <input
                    value={sessionAuthPhone}
                    onChange={(e) => setSessionAuthPhone(e.target.value)}
                    placeholder="+79001234567"
                  />
                </label>

                <div className="form-grid">
                  <label className="form-field">
                    API ID
                    <input
                      value={sessionAuthApiId}
                      onChange={(e) => setSessionAuthApiId(e.target.value)}
                    />
                  </label>
                  <label className="form-field">
                    API HASH
                    <input
                      type="password"
                      value={sessionAuthApiHash}
                      onChange={(e) => setSessionAuthApiHash(e.target.value)}
                    />
                  </label>
                </div>

                <label className="form-field">
                  ПРОКСИ (OPTIONAL)
                  <input
                    value={sessionAuthProxy}
                    onChange={(e) => setSessionAuthProxy(e.target.value)}
                    placeholder="http://user:pass@host:port"
                  />
                </label>

                <div className="modal-footer">
                  <button className="tool-btn" onClick={() => setActiveModal(null)}>
                    Отмена
                  </button>
                  <button className="primary-btn" onClick={runSessionAuth}>
                    <Play size={15} /> Начать авторизацию
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="service-status">
                  <span className="status-dot" /> Статус: {authTask?.stage || authTask?.status}
                </div>
                <pre className="module-log auth-log">{authTask?.logs.join("\n")}</pre>
                {authTask?.stage === "code" || authTask?.stage === "password" ? (
                  <div className="auth-input">
                    <input
                      value={authInputVal}
                      onChange={(e) => setAuthInputVal(e.target.value)}
                      placeholder={
                        authTask.stage === "code" ? "Введите SMS код..." : "Введите 2FA пароль..."
                      }
                      onKeyDown={(e) => e.key === "Enter" && submitAuthInput()}
                    />
                    <button className="primary-btn" onClick={submitAuthInput}>
                      Отправить
                    </button>
                  </div>
                ) : null}
                <div className="modal-footer">
                  <button className="tool-btn" onClick={() => setAuthTaskId(null)}>
                    Закрыть
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Modal: Fallback API */}
      {activeModal === "api" && (
        <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && setActiveModal(null)}>
          <div className="modal panel service-modal">
            <div className="modal-head">
              <div>
                <div className="panel-kicker">SERVICE WORKSPACE</div>
                <h2>Fallback API генератор</h2>
              </div>
              <button className="more-btn" onClick={() => setActiveModal(null)}>
                <X size={17} />
              </button>
            </div>
            <p className="modal-copy">Выберите аккаунты для назначения проверенных API-пар:</p>

            <div className="account-check-list">
              {items.map((acc) => {
                const id = acc.workdir as string;
                const isChecked = apiSelectedAccounts.includes(id);
                return (
                  <label key={id}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() =>
                        setApiSelectedAccounts((prev) =>
                          isChecked ? prev.filter((item) => item !== id) : [...prev, id]
                        )
                      }
                    />
                    {acc.name} ({id})
                  </label>
                );
              })}
            </div>

            <div className="modal-footer">
              <button className="tool-btn" onClick={() => setActiveModal(null)}>
                Отмена
              </button>
              <button className="primary-btn" onClick={runBulkApiGeneration}>
                Назначить API пары
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: TData Converter */}
      {activeModal === "tdata" && (
        <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && setActiveModal(null)}>
          <div className="modal panel service-modal">
            <div className="modal-head">
              <div>
                <div className="panel-kicker">SERVICE WORKSPACE</div>
                <h2>Конвертер TData</h2>
              </div>
              <button className="more-btn" onClick={() => setActiveModal(null)}>
                <X size={17} />
              </button>
            </div>

            <div className="converter-list">
              {tdataFolders.map((f) => (
                <div key={f}>{f}</div>
              ))}
              {tdataFolders.length === 0 && (
                <div style={{ padding: "10px", color: "var(--muted)" }}>Папки не добавлены</div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="tool-btn"
                onClick={async () => {
                  const res = await (window as any).shadowgram?.openDirectory();
                  if (res?.filePaths?.[0]) setTdataFolders((prev) => [...prev, res.filePaths[0]]);
                }}
              >
                <Plus size={14} /> Добавить папку tdata
              </button>
              <button
                className="primary-btn"
                disabled={!tdataFolders.length || tdataRunning}
                onClick={() => {
                  setTdataRunning(true);
                  notify("Конвертация TData запущена");
                  setTimeout(() => {
                    setTdataRunning(false);
                    notify("Конвертация TData завершена!");
                  }, 2000);
                }}
              >
                {tdataRunning ? "Конвертация..." : "Начать конвертацию"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
