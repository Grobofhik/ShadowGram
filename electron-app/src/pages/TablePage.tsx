import React, { useEffect, useMemo, useState } from "react";
import { Download, RefreshCw, Wifi } from "lucide-react";
import { AccountRecord } from "../types";

export function TablePage({ notify }: { notify: (msg: string) => void }) {
  const [accounts, setAccounts] = useState<AccountRecord[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [proxy, setProxy] = useState("");
  const load = async () => setAccounts((await (window as any).shadowgram?.listAccountTable())?.accounts || []);
  useEffect(() => { void load(); }, []);
  const selectedAccounts = useMemo(() => accounts.filter((a) => selected.includes(a.workdir)), [accounts, selected]);
  const toggle = (workdir: string) => setSelected((old) => old.includes(workdir) ? old.filter((v) => v !== workdir) : [...old, workdir]);
  const bulk = async (method: string, payload: Record<string, unknown> = {}) => {
    const result = await (window as any).shadowgram?.[method]({ workdirs: selected, ...payload });
    if (result?.accounts) setAccounts(result.accounts);
    notify(result?.message || "Операция выполнена");
  };
  return <div className="page"><section className="page-hero"><div><div className="hero-kicker"><Wifi size={15} /> ACCOUNT TABLE</div><h2>Сводная таблица аккаунтов</h2></div><div className="top-actions"><button className="icon-btn" onClick={() => void load()}><RefreshCw size={16} /></button><button className="tool-btn" onClick={async () => { const r = await (window as any).shadowgram?.exportAccountsCsv(); if (!r?.canceled) notify(r?.message || "CSV сохранён"); }}><Download size={14} /> Скачать CSV</button></div></section>
    <div className="panel table-panel"><div className="table-actions"><input value={proxy} onChange={(e) => setProxy(e.target.value)} placeholder="Прокси для выбранных..." /><button className="tool-btn" disabled={!selected.length} onClick={() => void bulk("bulkSetProxy", { proxy })}>Установить Proxy</button><button className="tool-btn" disabled={!selected.length} onClick={() => void bulk("bulkSetApi")}>Обновить API ключи</button><button className="primary-btn" disabled={!selected.length} onClick={() => void bulk("bulkCheckProxy")}>Проверить прокси</button></div>
      <div className="data-table"><div className="data-row data-head"><span>✓</span><span>Имя</span><span>Телефон</span><span>Privacy Guard</span><span>API ID</span><span>Proxy</span><span>Устройство</span><span>Заметки</span></div>{accounts.map((a) => <div className="data-row" key={a.workdir}><span><input type="checkbox" checked={selected.includes(a.workdir)} onChange={() => toggle(a.workdir)} /></span><span>{a.name}</span><span>{a.phone || ""}</span><span>{a.privacy_guard ? "АКТИВЕН" : "УЯЗВИМ"}</span><span>{a.api_id || ""}</span><span>{a.proxy_url || ""}</span><span>{a.device_name || ""}</span><span>{a.notes || ""}</span></div>)}</div></div></div>;
}
