export type Page =
  | "Dashboard"
  | "Accounts"
  | "Create"
  | "Table"
  | "Server"
  | "Modules"
  | "Neuro"
  | "Mass Sender"
  | "AI Assistant"
  | "Node Editor"
  | "Services"
  | "Documentation"
  | "Settings";

export type NodeSpecParamOption = {
  value: string;
  label: string;
};

export type NodeSpecParam = {
  label: string;
  type: string; // "int" | "str" | "select" | "textarea" | "bool"
  default?: unknown;
  options?: NodeSpecParamOption[];
};

export type NodeSpec = {
  title: string;
  category: string;
  inputs: string[];
  outputs: string[];
  params: Record<string, NodeSpecParam>;
};

export type NodeData = {
  id: string;
  type: string;
  x: number;
  y: number;
  params: Record<string, string>;
};

export type NodeConnection = {
  fromNode: string;
  fromPort: string;
  toNode: string;
  toPort: string;
};

export type GraphData = {
  nodes: NodeData[];
  connections: NodeConnection[];
};

export type TaskRecord = {
  taskId: string;
  name: string;
  status: string;
  stage?: string;
  logs: string[];
  createdAt?: string | number;
};

export type AccountRecord = {
  name: string;
  workdir: string;
  status: string;
  proxyStatus: string;
  device_name?: string;
  notes?: string;
  ai_prompt?: boolean | string;
  phone?: string;
  email?: string;
  password?: string;
  api_id?: string | number;
  api_hash?: string;
  proxy_url?: string;
  first_name?: string;
  last_name?: string;
  username?: string;
  privacy_guard?: boolean;
  color?: string;
  [key: string]: unknown;
};

export type ScheduleRecord = {
  id: string;
  name: string;
  interval: number;
  unit: string;
  enabled?: boolean;
  scenario?: unknown;
  [key: string]: unknown;
};

export type ModuleRecord = {
  name: string;
  title: string;
  description?: string;
  params?: Array<{
    name: string;
    type: string;
    label: string;
    default?: unknown;
    options?: Array<{ value: string; label: string }>;
  }>;
};

export type FarmRecord = {
  name: string;
  is_active: boolean;
};
