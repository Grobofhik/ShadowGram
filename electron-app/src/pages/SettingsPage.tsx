import React, { useState, useEffect } from "react";
import { Settings, Save, ShieldCheck, RefreshCw, Database } from "lucide-react";
import { FarmRecord } from "../types";

interface SettingsPageProps {
  notify: (msg: string) => void;
  onFarmChanged?: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ notify, onFarmChanged }) => {
  const [activeTab, setActiveTab] = useState<string>("farms");

  // General Settings
  const [maxTasks, setMaxTasks] = useState<string>("10");
  const [apiId, setApiId] = useState<string>("");
  const [apiHash, setApiHash] = useState<string>("");
  const [stealthMode, setStealthMode] = useState<boolean>(false);

  // Farms Management
  const [farms, setFarms] = useState<FarmRecord[]>([]);
  const [activeFarm, setActiveFarm] = useState<string>("main");
  const [selectedFarm, setSelectedFarm] = useState<string>("main");
  const [newFarmName, setNewFarmName] = useState<string>("");

  useEffect(() => {
    loadSettings();
    loadFarms();
  }, []);

  const loadSettings = async () => {
    const res = await (window as any).shadowgram?.getSettings();
    if (res?.settings) {
      if (res.settings.max_concurrent_tasks) setMaxTasks(String(res.settings.max_concurrent_tasks));
      if (res.settings.api_id) setApiId(String(res.settings.api_id));
      if (res.settings.api_hash) setApiHash(String(res.settings.api_hash));
      if (res.settings.stealth_mode) setStealthMode(Boolean(res.settings.stealth_mode));
    }
  };

  const loadFarms = async () => {
    const res = await (window as any).shadowgram?.getFarms();
    if (res?.farms) {
      setFarms(res.farms);
      const active = res.farms.find((f: any) => f.is_active)?.name || "main";
      setActiveFarm(active);
      setSelectedFarm(active);
    }
  };

  const saveGeneralSettings = async () => {
    const shadowgram = (window as any).shadowgram;
    await shadowgram?.saveSettings({
      settings: {
        max_concurrent_tasks: Number(maxTasks),
        api_id: apiId,
        api_hash: apiHash,
        stealth_mode: stealthMode,
      },
    });
    notify("Настройки сохранены");
  };

  const handleSwitchFarm = async () => {
    if (selectedFarm === activeFarm) return;
    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.switchFarm({ farm: selectedFarm });
    if (res?.ok) {
      setActiveFarm(selectedFarm);
      notify(`Переключено на ферму '${selectedFarm}'!`);
      if (onFarmChanged) onFarmChanged();
    } else {
      notify(res?.message || "Ошибка смены фермы");
    }
  };

  const handleCreateFarm = async () => {
    if (!newFarmName.trim()) {
      notify("Введите имя для новой фермы!");
      return;
    }
    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.createFarm({ name: newFarmName.trim() });
    if (res?.ok) {
      notify(`Ферма '${newFarmName.trim()}' успешно создана!`);
      setNewFarmName("");
      loadFarms();
    } else {
      notify(res?.message || "Ошибка создания фермы");
    }
  };

  return (
    <div className="page settings-page">
      <section className="page-hero">
        <div>
          <div className="hero-kicker">
            <Settings size={15} /> CONFIGURATION HUB
          </div>
          <h2>Настройки Системы</h2>
          <p>Управление глобальными лимитами, фермами, API и параметрами безопасности.</p>
        </div>
      </section>

      <div className="settings-layout">
        <aside className="settings-tabs">
          <button
            className={activeTab === "farms" ? "settings-tab active" : "settings-tab"}
            onClick={() => setActiveTab("farms")}
          >
            🚜 Управление фермами
          </button>
          <button
            className={activeTab === "general" ? "settings-tab active" : "settings-tab"}
            onClick={() => setActiveTab("general")}
          >
            ⚙️ Общие настройки
          </button>
        </aside>

        <section className="panel settings-content">
          {activeTab === "farms" && (
            <div className="settings-form">
              <div className="settings-section-title">
                <h3>Управление локальными фермами аккаунтов</h3>
                <span>Каждая ферма содержит отдельную папку с конфигурацией и профилями.</span>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <div className="panel-kicker">ТЕКУЩАЯ АКТИВНАЯ ФЕРМА</div>
                <div
                  style={{
                    fontSize: "20px",
                    fontWeight: "bold",
                    color: "var(--green)",
                    padding: "12px",
                    background: "#080e09",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    textAlign: "center",
                    margin: "8px 0 20px",
                  }}
                >
                  {activeFarm}
                </div>

                <div className="panel-kicker">ПЕРЕКЛЮЧИТЬ АКТИВНУЮ ФЕРМУ</div>
                <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                  <select
                    style={{ flex: 1, height: "40px" }}
                    value={selectedFarm}
                    onChange={(e) => setSelectedFarm(e.target.value)}
                  >
                    {farms.map((f) => (
                      <option key={f.name} value={f.name}>
                        {f.name} {f.is_active ? "(Активная)" : ""}
                      </option>
                    ))}
                  </select>
                  <button className="primary-btn" onClick={handleSwitchFarm}>
                    Переключить
                  </button>
                </div>
              </div>

              <div style={{ marginTop: "25px" }}>
                <div className="panel-kicker">СОЗДАТЬ НОВУЮ ФЕРМУ</div>
                <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                  <input
                    style={{ flex: 1, height: "40px" }}
                    value={newFarmName}
                    onChange={(e) => setNewFarmName(e.target.value)}
                    placeholder="Имя новой фермы (например: crypto_farm_02)..."
                  />
                  <button className="primary-btn" onClick={handleCreateFarm}>
                    Создать
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "general" && (
            <div className="settings-form">
              <div className="settings-section-title">
                <h3>Глобальные лимиты и Telegram API</h3>
                <span>Значения по умолчанию для работы потоков.</span>
              </div>

              <div className="form-grid">
                <label className="form-field">
                  МАКС. ПАРАЛЛЕЛЬНЫХ ЗАДАЧ
                  <input value={maxTasks} onChange={(e) => setMaxTasks(e.target.value)} />
                </label>
                <label className="form-field">
                  DEFAULT API ID
                  <input value={apiId} onChange={(e) => setApiId(e.target.value)} />
                </label>
              </div>

              <label className="form-field">
                DEFAULT API HASH
                <input
                  type="password"
                  value={apiHash}
                  onChange={(e) => setApiHash(e.target.value)}
                />
              </label>

              <div style={{ marginTop: "20px" }}>
                <button className="primary-btn" onClick={saveGeneralSettings}>
                  <Save size={15} /> Сохранить настройки
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
