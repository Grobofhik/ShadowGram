import React, { useState } from "react";
import { Server } from "lucide-react";

export function ServerPage({ notify }: { notify: (msg: string) => void }) {
  const [host, setHost] = useState("127.0.0.1"); const [port, setPort] = useState("8765"); const [token, setToken] = useState(""); const [result, setResult] = useState("");
  const ping = async () => { const r = await (window as any).shadowgram?.pingServer({ host, port: Number(port), token }); setResult(r?.message || "Нет ответа"); notify(r?.ok ? "Сервер доступен" : "Сервер недоступен"); };
  return <div className="page"><section className="page-hero"><div><div className="hero-kicker"><Server size={15} /> SERVER CONTROL</div><h2>Управление сервером</h2></div></section><div className="panel form-panel"><label className="form-field">HOST<input value={host} onChange={(e) => setHost(e.target.value)} /></label><label className="form-field">PORT<input value={port} onChange={(e) => setPort(e.target.value)} /></label><label className="form-field">TOKEN<input type="password" value={token} onChange={(e) => setToken(e.target.value)} /></label><button className="primary-btn" onClick={() => void ping()}>Проверить соединение</button>{result && <pre className="module-log">{result}</pre>}</div></div>;
}
