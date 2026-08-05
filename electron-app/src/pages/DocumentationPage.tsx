import React, { useEffect, useState } from "react";
import { FileText } from "lucide-react";

export function DocumentationPage({ notify }: { notify: (msg: string) => void }) {
  const [files, setFiles] = useState<string[]>([]); const [selected, setSelected] = useState(""); const [content, setContent] = useState("");
  useEffect(() => { void (async () => setFiles((await (window as any).shadowgram?.listDocs())?.files || []))(); }, []);
  const read = async (path: string) => { setSelected(path); const r = await (window as any).shadowgram?.readDoc({ path }); setContent(r?.content || ""); };
  return <div className="page"><section className="page-hero"><div><div className="hero-kicker"><FileText size={15} /> DOCUMENTATION</div><h2>Документация ShadowGram</h2></div></section><div className="docs-layout"><div className="panel docs-list">{files.map((file) => <button className={selected === file ? "doc-item active" : "doc-item"} key={file} onClick={() => void read(file)}>{file}</button>)}</div><article className="panel doc-content">{content ? <pre>{content}</pre> : <p className="muted-copy">Выберите документ.</p>}</article></div></div>;
}
