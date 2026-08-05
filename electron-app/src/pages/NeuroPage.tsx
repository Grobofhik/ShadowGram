import React, { useState, useEffect } from "react";
import { BrainCircuit, Play, Save } from "lucide-react";
import { AccountRecord } from "../types";

interface NeuroPageProps {
  accounts: AccountRecord[];
  notify: (msg: string) => void;
}

export const NeuroPage: React.FC<NeuroPageProps> = ({ accounts: items, notify }) => {
  const [channels, setChannels] = useState<string>("https://t.me/durov\n@telegram");
  const [mode, setMode] = useState<string>("0");
  const [subDelay, setSubDelay] = useState<string>("10");
  const [comDelay, setComDelay] = useState<string>("30");
  const [chanMin, setChanMin] = useState<string>("1");
  const [chanMax, setChanMax] = useState<string>("5");
  const [readHistory, setReadHistory] = useState<boolean>(true);

  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [logs, setLogs] = useState<string>("NEURO_ENGINE_READY...");
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);

  useEffect(() => {
    // Load neuro_v2 settings from config
    void (window as any).shadowgram
      ?.getSettings()
      .then((res: any) => {
        const neuro = res?.settings?.neuro_v2 || {};
        if (neuro.channels) setChannels(neuro.channels);
        if (neuro.mode !== undefined) setMode(String(neuro.mode));
        if (neuro.subDelay) setSubDelay(String(neuro.subDelay));
        if (neuro.comDelay) setComDelay(String(neuro.comDelay));
        if (neuro.prompts) setPrompts(neuro.prompts);
      })
      .catch(() => undefined);

    setSelectedAccounts(items.map((acc) => acc.name || (acc.workdir as string)));
  }, [items]);

  const saveSettings = async () => {
    const shadowgram = (window as any).shadowgram;
    await shadowgram?.saveSettings({
      settings: {
        neuro_v2: {
          channels,
          mode: Number(mode),
          subDelay: Number(subDelay),
          comDelay: Number(comDelay),
          chanMin: Number(chanMin),
          chanMax: Number(chanMax),
          readHistory,
          prompts,
        },
      },
    });
    notify("Настройки Нейрокомментинга сохранены");
  };

  const runNeuro = async () => {
    if (!channels.trim()) {
      notify("Укажите хотя бы один целевой канал!");
      return;
    }

    if (!selectedAccounts.length) {
      notify("Выберите хотя бы один аккаунт для комментирования!");
      return;
    }

    await saveSettings();

    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.runNeuro({
      selectedAccounts,
      settings: {
        channels,
        mode: Number(mode),
        subDelay: Number(subDelay),
        comDelay: Number(comDelay),
      },
    });

    if (res?.ok && res.taskId) {
      setRunningTaskId(res.taskId);
      notify("Нейрокомментинг успешно запущен!");

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
      notify(res?.message || "Ошибка запуска нейрокомментинга");
    }
  };

  const stopNeuro = async () => {
    if (!runningTaskId) return;
    await (window as any).shadowgram?.stopTask({ taskId: runningTaskId });
    notify("Остановка Нейрокомментинга запрошена");
  };

  return (
    <div className="page neuro-page">
      <section className="page-hero">
        <div>
          <div className="hero-kicker">
            <BrainCircuit size={15} /> AI COMMENT GRID
          </div>
          <h2>Нейрокомментинг (NeuroV2)</h2>
          <p>
            Автоматическое отслеживание постов в Telegram-каналах и генерация ответов через нейросеть.
          </p>
        </div>
        <button className="tool-btn" onClick={saveSettings}>
          <Save size={15} /> Сохранить настройки
        </button>
      </section>

      <div className="neuro-top">
        <section className="panel">
          <div className="panel-kicker">ЦЕЛЕВЫЕ КАНАЛЫ (ОДИН НА СТРОКУ)</div>
          <textarea
            className="targets-editor neuro-channels"
            value={channels}
            onChange={(e) => setChannels(e.target.value)}
            placeholder="https://t.me/durov&#10;@telegram"
          />
        </section>

        <section className="panel">
          <div className="panel-kicker">РЕЖИМ И ЗАДЕРЖКИ</div>
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="0">Делить каналы поровну между аккаунтами</option>
            <option value="1">Каждый аккаунт подписывается на все каналы</option>
          </select>

          <div className="form-grid">
            <label className="form-field">
              ЗАДЕРЖКА ПОДПИСКИ (СЕК)
              <input value={subDelay} onChange={(e) => setSubDelay(e.target.value)} />
            </label>
            <label className="form-field">
              ЗАДЕРЖКА КОММЕНТАРИЯ (СЕК)
              <input value={comDelay} onChange={(e) => setComDelay(e.target.value)} />
            </label>
            <label className="form-field">
              КАНАЛОВ МИН
              <input value={chanMin} onChange={(e) => setChanMin(e.target.value)} />
            </label>
            <label className="form-field">
              КАНАЛОВ МАКС
              <input value={chanMax} onChange={(e) => setChanMax(e.target.value)} />
            </label>
          </div>
        </section>
      </div>

      <section className="panel neuro-activity" style={{ marginTop: "15px" }}>
        <div className="panel-head">
          <div>
            <div className="panel-kicker">АККАУНТЫ И ПРОМПТЫ</div>
            <h3>Выбор аккаунтов и настройка ролей</h3>
          </div>
          {runningTaskId ? (
            <button className="danger-btn" onClick={stopNeuro}>
              Остановить
            </button>
          ) : (
            <button className="primary-btn" onClick={runNeuro}>
              <Play size={15} /> Запустить Нейрокомментинг
            </button>
          )}
        </div>

        <div className="neuro-table">
          {items.map((acc) => {
            const accId = acc.name || (acc.workdir as string);
            const isChecked = selectedAccounts.includes(accId);
            return (
              <div className="neuro-row" key={accId}>
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() =>
                    setSelectedAccounts((prev) =>
                      isChecked ? prev.filter((id) => id !== accId) : [...prev, accId]
                    )
                  }
                />
                <b>{accId}</b>
                <input
                  className="prompt-input"
                  style={{
                    flex: 1,
                    background: "#080e09",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    color: "#e1ede4",
                    padding: "6px 9px",
                    fontSize: "11px",
                  }}
                  value={prompts[accId] || ""}
                  onChange={(e) => setPrompts({ ...prompts, [accId]: e.target.value })}
                  placeholder="Индивидуальный AI промпт для этого аккаунта..."
                />
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: "18px" }}>
          <div className="panel-kicker">LIVE ЛОГ НЕЙРОСЕТИ</div>
          <pre className="module-log">{logs}</pre>
        </div>
      </section>
    </div>
  );
};
