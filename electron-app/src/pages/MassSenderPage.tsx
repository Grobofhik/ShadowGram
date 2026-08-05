import React, { useState, useEffect } from "react";
import { Send, Play, Image, FileText, HelpCircle } from "lucide-react";
import { AccountRecord } from "../types";

interface MassSenderPageProps {
  accounts: AccountRecord[];
  notify: (msg: string) => void;
}

export const MassSenderPage: React.FC<MassSenderPageProps> = ({ accounts: items, notify }) => {
  const [targetsText, setTargetsText] = useState<string>("");
  const [messageText, setMessageText] = useState<string>("");
  const [delayMin, setDelayMin] = useState<string>("5");
  const [delayMax, setDelayMax] = useState<string>("15");
  const [limitPerAcc, setLimitPerAcc] = useState<string>("20");

  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
  const [logs, setLogs] = useState<string>("MASS_SENDER_READY...");
  const [stats, setStats] = useState({ sent: 0, failed: 0, flood: 0 });

  useEffect(() => {
    setSelectedAccounts(items.map((acc) => acc.name || (acc.workdir as string)));
  }, [items]);

  // Spin-tax template helper: {Привет|Здравствуйте|Добрый день}
  const applyFormatting = (tag: string) => {
    if (tag === "b") setMessageText((prev) => prev + "<b>жирный</b>");
    if (tag === "i") setMessageText((prev) => prev + "<i>курсив</i>");
    if (tag === "spintax") setMessageText((prev) => prev + "{Привет|Здравствуйте|Добрый день}");
  };

  const runMassSender = async () => {
    const targets = targetsText
      .split("\n")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    if (!targets.length) {
      notify("Введите хотя бы одного получателя (юзернейм или ID)!");
      return;
    }
    if (!messageText.trim()) {
      notify("Введите текст сообщения для рассылки!");
      return;
    }

    const selectedAccObjects = items.filter((acc) =>
      selectedAccounts.includes(acc.name || (acc.workdir as string))
    );

    if (!selectedAccObjects.length) {
      notify("Выберите хотя бы один аккаунт для отправки!");
      return;
    }

    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.runMassSender({
      accounts: selectedAccObjects,
      targets,
      message: messageText,
      delayMin: Number(delayMin),
      delayMax: Number(delayMax),
      limitPerAccount: Number(limitPerAcc),
    });

    if (res?.ok && res.taskId) {
      setRunningTaskId(res.taskId);
      notify("Массовая рассылка запущена!");

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
      notify(res?.message || "Ошибка запуска рассылки");
    }
  };

  const stopMassSender = async () => {
    if (!runningTaskId) return;
    await (window as any).shadowgram?.stopTask({ taskId: runningTaskId });
    notify("Остановка рассылки запрошена");
  };

  return (
    <div className="page sender-page">
      <section className="page-hero">
        <div>
          <div className="hero-kicker">
            <Send size={15} /> BULK DISPATCHER
          </div>
          <h2>Массовая рассылка</h2>
          <p>
            Рассылка сообщений в личные сообщения и группы с поддержкой рандомизации текста (Spin-tax).
          </p>
        </div>
      </section>

      <div className="sender-layout">
        {/* Left composer section */}
        <section className="panel composer">
          <div className="panel-kicker">СОСТАВЛЕНИЕ СООБЩЕНИЯ</div>

          <div className="format-toolbar" style={{ margin: "10px 0" }}>
            <button type="button" onClick={() => applyFormatting("b")}>
              <b>B</b> Жирный
            </button>
            <button type="button" onClick={() => applyFormatting("i")}>
              <i>I</i> Курсив
            </button>
            <button type="button" className="emoji-btn" onClick={() => applyFormatting("spintax")}>
              {"{Spin|tax}"}
            </button>
          </div>

          <textarea
            className="message-editor"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder="Введите текст сообщения или рандомизацию {Вариант1|Вариант2}..."
          />

          <div className="telegram-preview">
            <div style={{ fontSize: "11px", color: "var(--green)", marginBottom: "4px" }}>
              ПРЕДПРОСМОТР TELEGRAM
            </div>
            <p>{messageText || "Ваше сообщение отобразится здесь..."}</p>
          </div>

          <div className="panel-kicker" style={{ marginTop: "15px" }}>
            ПОЛУЧАТЕЛИ (ОДИН ИЛИ ССЫЛКА НА СТРОКУ)
          </div>
          <textarea
            className="targets-editor"
            value={targetsText}
            onChange={(e) => setTargetsText(e.target.value)}
            placeholder="@username&#10;https://t.me/username&#10;+79001234567"
          />
        </section>

        {/* Right Settings and Status section */}
        <section className="panel sender-side">
          <div className="panel-kicker">НАСТРОЙКИ РАССЫЛКИ</div>

          <div className="form-grid" style={{ margin: "10px 0" }}>
            <label className="form-field">
              ПАУЗА МИН (СЕК)
              <input value={delayMin} onChange={(e) => setDelayMin(e.target.value)} />
            </label>
            <label className="form-field">
              ПАУЗА МАКС (СЕК)
              <input value={delayMax} onChange={(e) => setDelayMax(e.target.value)} />
            </label>
          </div>

          <label className="form-field">
            ЛИМИТ НА АККАУНТ
            <input value={limitPerAcc} onChange={(e) => setLimitPerAcc(e.target.value)} />
          </label>

          <div style={{ margin: "15px 0" }}>
            <div className="panel-kicker">ВЫБОР АККАУНТОВ-ОТПРАВИТЕЛЕЙ ({selectedAccounts.length})</div>
            <div className="account-check-list" style={{ maxHeight: "180px", overflowY: "auto" }}>
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
                    {accId}
                  </label>
                );
              })}
            </div>
          </div>

          <div className="send-actions" style={{ marginBottom: "15px" }}>
            {runningTaskId ? (
              <button className="danger-btn" onClick={stopMassSender} style={{ width: "100%" }}>
                Остановить рассылку
              </button>
            ) : (
              <button className="primary-btn" onClick={runMassSender} style={{ width: "100%" }}>
                <Send size={15} /> Начать массовую рассылку
              </button>
            )}
          </div>

          <div className="panel-kicker">ЛОГ И СТАТИСТИКА</div>
          <pre className="sender-log">{logs}</pre>
        </section>
      </div>
    </div>
  );
};
