import React, { useState, useEffect, useRef } from "react";
import {
  Workflow,
  Play,
  Users,
  Search,
  SlidersHorizontal,
  Plus,
  Trash2,
  Maximize2,
  Minimize2,
} from "lucide-react";
import {
  NodeSpec,
  NodeData,
  NodeConnection,
  AccountRecord,
} from "../types";
import { EmptyParamsFillDialog } from "../dialogs/EmptyParamsFillDialog";

interface NodeEditorPageProps {
  accounts: AccountRecord[];
  notify: (msg: string) => void;
}

export const NodeEditorPage: React.FC<NodeEditorPageProps> = ({
  accounts: items,
  notify,
}) => {
  const [specs, setSpecs] = useState<Record<string, NodeSpec>>({});
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [connections, setConnections] = useState<NodeConnection[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedConnectionIndex, setSelectedConnectionIndex] = useState<number | null>(null);

  // Connecting wire state
  const [connectingFrom, setConnectingFrom] = useState<{
    nodeId: string;
    portName: string;
    isOutput: boolean;
  } | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Pan & Zoom
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(1);
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [startPan, setStartPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Dragging node
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Execution & Logs
  const [logs, setLogs] = useState<string>("NODE_EDITOR_READY...");
  const [accountPanel, setAccountPanel] = useState<boolean>(true);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);

  // Pre-launch fill dialog
  const [showFillDialog, setShowFillDialog] = useState<boolean>(false);
  const [emptyFieldsToFill, setEmptyFieldsToFill] = useState<any[]>([]);

  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Fetch specs from backend
    void (window as any).shadowgram
      ?.getNodeSpecs()
      .then((response: any) => {
        if (response?.specs) setSpecs(response.specs);
      })
      .catch(() => undefined);

    setSelectedAccounts(items.map((acc) => acc.name || (acc.workdir as string)));
  }, [items]);

  // Group specs by category
  const categories = Object.entries(specs).reduce<Record<string, Array<[string, NodeSpec]>>>(
    (grouped, [key, spec]) => {
      const cat = spec.category || "Общие";
      (grouped[cat] = grouped[cat] || []).push([key, spec]);
      return grouped;
    },
    {}
  );

  // Node Management
  const addNode = (type: string) => {
    const spec = specs[type];
    if (!spec) return;

    const id = `${type}-${Date.now()}`;
    const defaultParams: Record<string, string> = {};
    if (spec.params) {
      Object.entries(spec.params).forEach(([paramKey, paramInfo]) => {
        defaultParams[paramKey] = String(paramInfo.default ?? "");
      });
    }

    // Place near center with slight offset
    const newNode: NodeData = {
      id,
      type,
      x: 100 + (nodes.length % 5) * 210 - pan.x,
      y: 100 + Math.floor(nodes.length / 5) * 120 - pan.y,
      params: defaultParams,
    };

    setNodes((prev) => [...prev, newNode]);
    setSelectedNodeId(id);
  };

  const deleteNode = (id: string) => {
    setNodes((prev) => prev.filter((n) => n.id !== id));
    setConnections((prev) => prev.filter((c) => c.fromNode !== id && c.toNode !== id));
    if (selectedNodeId === id) setSelectedNodeId(null);
  };

  const updateParam = (paramName: string, val: string) => {
    if (!selectedNodeId) return;
    setNodes((prev) =>
      prev.map((n) => (n.id === selectedNodeId ? { ...n, params: { ...n.params, [paramName]: val } } : n))
    );
  };

  // Wire Connection Dragging
  const handlePortMouseDown = (
    e: React.MouseEvent,
    nodeId: string,
    portName: string,
    isOutput: boolean
  ) => {
    e.stopPropagation();
    setConnectingFrom({ nodeId, portName, isOutput });
  };

  const handlePortMouseUp = (
    e: React.MouseEvent,
    nodeId: string,
    portName: string,
    isOutput: boolean
  ) => {
    e.stopPropagation();
    if (!connectingFrom) return;

    // Disallow output-to-output or input-to-input or self-connection
    if (connectingFrom.isOutput === isOutput || connectingFrom.nodeId === nodeId) {
      setConnectingFrom(null);
      return;
    }

    const fromNode = connectingFrom.isOutput ? connectingFrom.nodeId : nodeId;
    const fromPort = connectingFrom.isOutput ? connectingFrom.portName : portName;
    const toNode = connectingFrom.isOutput ? nodeId : connectingFrom.nodeId;
    const toPort = connectingFrom.isOutput ? portName : connectingFrom.portName;

    // Prevent duplicates
    const exists = connections.some(
      (c) => c.fromNode === fromNode && c.fromPort === fromPort && c.toNode === toNode && c.toPort === toPort
    );

    if (!exists) {
      setConnections((prev) => [...prev, { fromNode, fromPort, toNode, toPort }]);
    }
    setConnectingFrom(null);
  };

  // Canvas Mouse Events (Pan & Node Drag)
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.target === canvasRef.current || (e.target as HTMLElement).classList.contains("canvas-grid")) {
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      setSelectedNodeId(null);
      setSelectedConnectionIndex(null);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const curMouseX = (e.clientX - rect.left - pan.x) / zoom;
    const curMouseY = (e.clientY - rect.top - pan.y) / zoom;
    setMousePos({ x: curMouseX, y: curMouseY });

    if (isPanning) {
      setPan({ x: e.clientX - startPan.x, y: e.clientY - startPan.y });
    }

    if (draggingNodeId) {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === draggingNodeId
            ? { ...n, x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y }
            : n
        )
      );
    }
  };

  const handleCanvasMouseUp = () => {
    setIsPanning(false);
    setDraggingNodeId(null);
    setConnectingFrom(null);
  };

  const handleNodeHeaderMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    setSelectedNodeId(nodeId);
    setSelectedConnectionIndex(null);
    setDraggingNodeId(nodeId);
    const node = nodes.find((n) => n.id === nodeId);
    if (node) {
      setDragOffset({ x: e.clientX - node.x, y: e.clientY - node.y });
    }
  };

  // Save / Load
  const saveScenario = async () => {
    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.saveFile({
      defaultPath: "scenario.sgn",
      filters: [{ name: "ShadowGram Nodes", extensions: ["sgn"] }],
    });
    if (res?.canceled || !res?.filePath) return;

    await shadowgram?.saveScenario({
      path: res.filePath,
      graph: { nodes, connections },
    });
    notify("Сценарий сохранён в файл");
  };

  const loadScenario = async () => {
    const shadowgram = (window as any).shadowgram;
    const res = await shadowgram?.openFile({
      properties: ["openFile"],
      filters: [{ name: "ShadowGram Nodes", extensions: ["sgn"] }],
    });
    if (res?.canceled || !res?.filePaths?.[0]) return;

    const loaded = await shadowgram?.loadScenario({ path: res.filePaths[0] });
    if (loaded?.graph) {
      setNodes(loaded.graph.nodes || []);
      setConnections(loaded.graph.connections || []);
      notify("Сценарий успешно загружен");
    }
  };

  // Pre-launch validation & Execution
  const checkEmptyParamsAndRun = () => {
    if (!nodes.some((n) => n.type === "start")) {
      notify("Добавьте узел 'Старт' перед запуском сценария!");
      return;
    }

    // Check for empty string params
    const emptyFields: any[] = [];
    nodes.forEach((node) => {
      const spec = specs[node.type];
      if (!spec || !spec.params) return;

      Object.entries(spec.params).forEach(([paramKey, paramInfo]) => {
        const val = (node.params[paramKey] ?? "").trim();
        // Check if string param requires text (e.g. url, text, channel, username, target)
        const isStringLike = paramInfo.type === "str" || paramInfo.type === "textarea";
        if (isStringLike && !val) {
          emptyFields.push({
            nodeId: node.id,
            nodeTitle: spec.title || node.type,
            paramKey,
            paramLabel: paramInfo.label || paramKey,
            defaultValue: String(paramInfo.default ?? ""),
          });
        }
      });
    });

    if (emptyFields.length > 0) {
      setEmptyFieldsToFill(emptyFields);
      setShowFillDialog(true);
    } else {
      executeGraph(nodes);
    }
  };

  const handleFillDialogConfirm = (filledValues: Record<string, Record<string, string>>) => {
    const updatedNodes = nodes.map((node) => {
      if (filledValues[node.id]) {
        return {
          ...node,
          params: { ...node.params, ...filledValues[node.id] },
        };
      }
      return node;
    });

    setNodes(updatedNodes);
    setShowFillDialog(false);
    executeGraph(updatedNodes);
  };

  const executeGraph = async (currentNodes: NodeData[]) => {
    const shadowgram = (window as any).shadowgram;
    const selectedAccObjects = items.filter((acc) =>
      selectedAccounts.includes(acc.name || (acc.workdir as string))
    );

    const result = await shadowgram?.runScenario({
      graph: { nodes: currentNodes, connections },
      accounts: selectedAccObjects,
    });

    setLogs(
      `[runner] ${result?.message ?? "Сценарий запущен"}\n[runner] Выбрано аккаунтов: ${selectedAccObjects.length}`
    );

    if (!result?.ok || !result.taskId) {
      notify(result?.message ?? "Ошибка запуска сценария");
      return;
    }

    setRunningTaskId(result.taskId);
    notify("Выполнение сценария начато!");

    // Polling log status
    const poll = async () => {
      const statusRes = await shadowgram?.getScenarioStatus({ taskId: result.taskId });
      if (statusRes?.logs?.length) {
        setLogs(statusRes.logs.join("\n"));
      }

      if (statusRes?.status === "running" || statusRes?.status === "stopping") {
        setTimeout(poll, 1000);
      } else {
        setRunningTaskId(null);
      }
    };
    void poll();
  };

  const stopScenario = async () => {
    if (!runningTaskId) return;
    await (window as any).shadowgram?.stopScenario({ taskId: runningTaskId });
    notify("Запрошена остановка сценария");
  };

  // Helper to compute port position on canvas
  const getPortCoordinates = (nodeId: string, portName: string, isOutput: boolean) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };

    const spec = specs[node.type];
    const ports = isOutput ? spec?.outputs || [] : spec?.inputs || [];
    const portIndex = ports.indexOf(portName);

    const nodeWidth = 190;
    const headerHeight = 36;
    const portSpacing = 22;

    const x = isOutput ? node.x + nodeWidth : node.x;
    const y = node.y + headerHeight + 16 + (portIndex >= 0 ? portIndex : 0) * portSpacing;

    return { x, y };
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  return (
    <div className="node-editor-shell">
      {/* Top Toolbar */}
      <div className="node-toolbar">
        <button
          className="tool-btn"
          onClick={() => setAccountPanel(!accountPanel)}
          title="Показать/скрыть аккаунты"
        >
          <Users size={14} /> Аккаунты ({selectedAccounts.length})
        </button>

        {Object.entries(categories).map(([category, entries]) => (
          <div className="node-menu" key={category}>
            <button className="tool-btn">{category} ▼</button>
            <div className="node-menu-items">
              {entries.map(([typeKey, spec]) => (
                <button key={typeKey} onClick={() => addNode(typeKey)}>
                  {spec.title}
                </button>
              ))}
            </div>
          </div>
        ))}

        <span className="node-toolbar-spacer" />

        <button className="tool-btn" onClick={() => setZoom((z) => Math.min(z + 0.15, 2))}>
          <Maximize2 size={13} />
        </button>
        <button className="tool-btn" onClick={() => setZoom((z) => Math.max(z - 0.15, 0.5))}>
          <Minimize2 size={13} />
        </button>

        <button
          className="tool-btn"
          onClick={() => {
            setNodes([]);
            setConnections([]);
            setSelectedNodeId(null);
          }}
        >
          <Trash2 size={14} /> Очистить
        </button>
        <button className="tool-btn" onClick={saveScenario}>
          Сохранить .sgn
        </button>
        <button className="tool-btn" onClick={loadScenario}>
          Загрузить .sgn
        </button>

        {runningTaskId ? (
          <button className="danger-btn" onClick={stopScenario}>
            Остановить
          </button>
        ) : (
          <button className="primary-btn" onClick={checkEmptyParamsAndRun}>
            <Play size={14} /> Запустить Сценарий
          </button>
        )}
      </div>

      {/* Main Workspace Grid */}
      <div className="node-workspace">
        {/* Account Selector Sidebar */}
        <aside className={accountPanel ? "node-accounts" : "node-accounts hidden"}>
          <div className="panel-kicker">ВЫБОР АККАУНТОВ</div>
          <div className="node-account-search search">
            <Search size={14} />
            <input placeholder="Поиск аккаунта..." />
          </div>
          <div style={{ marginBottom: "10px" }}>
            <button
              className="text-btn"
              onClick={() =>
                setSelectedAccounts(
                  selectedAccounts.length === items.length
                    ? []
                    : items.map((a) => a.name || (a.workdir as string))
                )
              }
            >
              {selectedAccounts.length === items.length ? "Снять все" : "Выбрать все"}
            </button>
          </div>
          {items.map((acc) => {
            const accId = acc.name || (acc.workdir as string);
            const isChecked = selectedAccounts.includes(accId);
            return (
              <label key={accId}>
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() =>
                    setSelectedAccounts((prev) =>
                      isChecked ? prev.filter((id) => id !== accId) : [...prev, accId]
                    )
                  }
                />
                {accId}
              </label>
            );
          })}
        </aside>

        {/* Canvas Area */}
        <section
          className="node-canvas"
          ref={canvasRef}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
        >
          <div
            className="canvas-grid"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "0 0",
            }}
          />

          <div
            className="nodes-container"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "0 0",
              position: "absolute",
              inset: 0,
            }}
          >
            {/* SVG Wires Connecting Ports */}
            <svg
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "5000px",
                height: "5000px",
                pointerEvents: "none",
              }}
            >
              {connections.map((conn, idx) => {
                const start = getPortCoordinates(conn.fromNode, conn.fromPort, true);
                const end = getPortCoordinates(conn.toNode, conn.toPort, false);

                const dx = Math.abs(end.x - start.x) * 0.5;
                const pathData = `M ${start.x} ${start.y} C ${start.x + dx} ${start.y}, ${end.x - dx} ${end.y}, ${end.x} ${end.y}`;
                const isSelected = selectedConnectionIndex === idx;

                return (
                  <path
                    key={`${conn.fromNode}-${conn.toNode}-${idx}`}
                    d={pathData}
                    fill="none"
                    stroke={isSelected ? "#34d399" : "#285e43"}
                    strokeWidth={isSelected ? 3.5 : 2.5}
                    style={{ pointerEvents: "stroke", cursor: "pointer" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedConnectionIndex(idx);
                      setSelectedNodeId(null);
                    }}
                  />
                );
              })}

              {/* Active Dragging Wire */}
              {connectingFrom && (
                <line
                  x1={
                    getPortCoordinates(
                      connectingFrom.nodeId,
                      connectingFrom.portName,
                      connectingFrom.isOutput
                    ).x
                  }
                  y1={
                    getPortCoordinates(
                      connectingFrom.nodeId,
                      connectingFrom.portName,
                      connectingFrom.isOutput
                    ).y
                  }
                  x2={mousePos.x}
                  y2={mousePos.y}
                  stroke="#34d399"
                  strokeDasharray="4"
                  strokeWidth="2"
                />
              )}
            </svg>

            {/* Nodes Render */}
            {nodes.map((node) => {
              const spec = specs[node.type] || {
                title: node.type,
                category: "Разное",
                inputs: [],
                outputs: [],
              };
              const isSelected = selectedNodeId === node.id;

              return (
                <div
                  key={node.id}
                  className={`node-card ${isSelected ? "selected" : ""}`}
                  style={{
                    left: `${node.x}px`,
                    top: `${node.y}px`,
                    position: "absolute",
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedNodeId(node.id);
                    setSelectedConnectionIndex(null);
                  }}
                >
                  <div
                    className="node-card-header"
                    onMouseDown={(e) => handleNodeHeaderMouseDown(e, node.id)}
                    style={{ cursor: "grab" }}
                  >
                    <span className="node-category">{spec.category}</span>
                    <b>{spec.title}</b>
                  </div>

                  {/* Ports Input/Output Layout */}
                  <div className="node-ports-row" style={{ display: "flex", justifyContent: "space-between" }}>
                    {/* Inputs */}
                    <div className="node-inputs" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {(spec.inputs || []).map((portName) => (
                        <div
                          key={portName}
                          className="port-dot input-port"
                          onMouseDown={(e) => handlePortMouseDown(e, node.id, portName, false)}
                          onMouseUp={(e) => handlePortMouseUp(e, node.id, portName, false)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            cursor: "crosshair",
                            fontSize: "10px",
                          }}
                        >
                          <span
                            style={{
                              width: "8px",
                              height: "8px",
                              borderRadius: "50%",
                              background: "#34d399",
                            }}
                          />
                          <small>{portName}</small>
                        </div>
                      ))}
                    </div>

                    {/* Outputs */}
                    <div className="node-outputs" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {(spec.outputs || []).map((portName) => (
                        <div
                          key={portName}
                          className="port-dot output-port"
                          onMouseDown={(e) => handlePortMouseDown(e, node.id, portName, true)}
                          onMouseUp={(e) => handlePortMouseUp(e, node.id, portName, true)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            justifyContent: "flex-end",
                            cursor: "crosshair",
                            fontSize: "10px",
                          }}
                        >
                          <small>{portName}</small>
                          <span
                            style={{
                              width: "8px",
                              height: "8px",
                              borderRadius: "50%",
                              background: "#60a5fa",
                            }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {nodes.length === 0 && (
            <div className="canvas-empty">
              <Workflow size={32} />
              <b>Конструктор сценариев</b>
              <span>Выберите узел из меню сверху или перетащите его на холст.</span>
            </div>
          )}
        </section>

        {/* Properties Side Panel */}
        <aside className="node-properties panel">
          {selectedNodeId && selectedNode && specs[selectedNode.type] ? (
            <>
              <div className="panel-kicker">СВОЙСТВА УЗЛА</div>
              <h3>{specs[selectedNode.type].title}</h3>

              {Object.entries(specs[selectedNode.type].params || {}).map(([pName, pInfo]) => (
                <label className="form-field" key={pName}>
                  {pInfo.label || pName}
                  {pInfo.type === "textarea" ? (
                    <textarea
                      value={selectedNode.params[pName] ?? ""}
                      onChange={(e) => updateParam(pName, e.target.value)}
                    />
                  ) : pInfo.type === "select" ? (
                    <select
                      value={selectedNode.params[pName] ?? String(pInfo.default ?? "")}
                      onChange={(e) => updateParam(pName, e.target.value)}
                    >
                      {(pInfo.options || []).map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={pInfo.type === "int" ? "number" : "text"}
                      value={selectedNode.params[pName] ?? ""}
                      onChange={(e) => updateParam(pName, e.target.value)}
                    />
                  )}
                </label>
              ))}

              <div style={{ marginTop: "20px" }}>
                <button className="danger-btn" onClick={() => deleteNode(selectedNode.id)}>
                  <Trash2 size={13} /> Удалить узел
                </button>
              </div>
            </>
          ) : selectedConnectionIndex !== null ? (
            <>
              <div className="panel-kicker">СВОЙСТВА СВЯЗИ</div>
              <h3>Соединение #{selectedConnectionIndex + 1}</h3>
              <p className="modal-copy">
                От: {connections[selectedConnectionIndex].fromNode} (
                {connections[selectedConnectionIndex].fromPort})<br />
                К: {connections[selectedConnectionIndex].toNode} (
                {connections[selectedConnectionIndex].toPort})
              </p>
              <button
                className="danger-btn"
                onClick={() => {
                  setConnections((prev) =>
                    prev.filter((_, idx) => idx !== selectedConnectionIndex)
                  );
                  setSelectedConnectionIndex(null);
                }}
              >
                Удалить связь
              </button>
            </>
          ) : (
            <div className="node-no-selection">
              <SlidersHorizontal size={22} />
              <span>Выберите узел или связь для настройки параметров.</span>
            </div>
          )}
        </aside>
      </div>

      {/* Bottom Live Console Log */}
      <div className="node-console">
        <div className="panel-kicker">
          КОНСОЛЬ ВЫПОЛНЕНИЯ {runningTaskId ? "· LIVE В ЭФИРЕ" : ""}
        </div>
        <pre>{logs}</pre>
      </div>

      {/* Pre-launch Empty Params Modal */}
      {showFillDialog && (
        <EmptyParamsFillDialog
          emptyFields={emptyFieldsToFill}
          onConfirm={handleFillDialogConfirm}
          onCancel={() => setShowFillDialog(false)}
        />
      )}
    </div>
  );
};
