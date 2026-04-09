"use client";

import { useState, useRef, useCallback } from "react";
import {
  FileText, Brain, Code, Search, RefreshCw, FlaskConical, Rocket,
  GitBranch, Layers, MessageSquare, Link, Wrench, CheckCircle,
  Plus, Trash2, Play, Save, Undo, Redo, ZoomIn, ZoomOut, Settings
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { PipelineConfig, PipelineNode, NodeType, NODE_TYPES } from "@/lib/pipeline-types";
import { NODE_TYPES as nodeTypesConfig, DEFAULT_PIPELINES } from "@/lib/pipeline-types";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  FileText, Brain, Code, Search, RefreshCw, FlaskConical, Rocket,
  GitBranch, Layers, MessageSquare, Link, Wrench, CheckCircle,
};

const COLOR_CLASSES: Record<string, { bg: string; border: string; text: string }> = {
  sky: { bg: "bg-sky-900/40", border: "border-sky-700", text: "text-sky-300" },
  violet: { bg: "bg-violet-900/40", border: "border-violet-700", text: "text-violet-300" },
  emerald: { bg: "bg-emerald-900/40", border: "border-emerald-700", text: "text-emerald-300" },
  amber: { bg: "bg-amber-900/40", border: "border-amber-700", text: "text-amber-300" },
  orange: { bg: "bg-orange-900/40", border: "border-orange-700", text: "text-orange-300" },
  teal: { bg: "bg-teal-900/40", border: "border-teal-700", text: "text-teal-300" },
  rose: { bg: "bg-rose-900/40", border: "border-rose-700", text: "text-rose-300" },
  yellow: { bg: "bg-yellow-900/40", border: "border-yellow-700", text: "text-yellow-300" },
  cyan: { bg: "bg-cyan-900/40", border: "border-cyan-700", text: "text-cyan-300" },
  indigo: { bg: "bg-indigo-900/40", border: "border-indigo-700", text: "text-indigo-300" },
  slate: { bg: "bg-slate-800/40", border: "border-slate-600", text: "text-slate-300" },
  stone: { bg: "bg-stone-800/40", border: "border-stone-600", text: "text-stone-300" },
  green: { bg: "bg-green-900/40", border: "border-green-700", text: "text-green-300" },
};

interface PipelineDesignerProps {
  initialPipeline?: PipelineConfig;
  onSave?: (pipeline: PipelineConfig) => void;
  onRun?: (pipeline: PipelineConfig) => void;
}

export function PipelineDesigner({ initialPipeline, onSave, onRun }: PipelineDesignerProps) {
  const [pipeline, setPipeline] = useState<PipelineConfig>(
    initialPipeline || DEFAULT_PIPELINES[0]
  );
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState<{ id: string; startX: number; startY: number } | null>(null);
  const [connecting, setConnecting] = useState<{ sourceId: string; sourcePort: string } | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const handleNodeDrag = useCallback((e: React.MouseEvent, nodeId: string) => {
    if (!dragging || dragging.id !== nodeId) return;

    const dx = (e.clientX - dragging.startX) / zoom;
    const dy = (e.clientY - dragging.startY) / zoom;

    setPipeline(prev => ({
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId
          ? { ...node, position: { x: node.position.x + dx, y: node.position.y + dy } }
          : node
      ),
    }));

    setDragging({ id: nodeId, startX: e.clientX, startY: e.clientY });
  }, [dragging, zoom]);

  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.preventDefault();
    setDragging({ id: nodeId, startX: e.clientX, startY: e.clientY });
    setSelectedNode(nodeId);
  };

  const handleMouseUp = () => {
    setDragging(null);
  };

  const addNode = (type: NodeType) => {
    const config = nodeTypesConfig[type];
    const id = `${type}-${Date.now()}`;
    const newNode: PipelineNode = {
      id,
      type,
      label: config.label,
      config: Object.fromEntries(config.configFields.map(f => [f.name, f.default])),
      position: { x: 200 + Math.random() * 200, y: 100 + Math.random() * 200 },
      inputs: [],
      outputs: [],
    };
    setPipeline(prev => ({
      ...prev,
      nodes: [...prev.nodes, newNode],
    }));
  };

  const deleteNode = (nodeId: string) => {
    setPipeline(prev => ({
      ...prev,
      nodes: prev.nodes.filter(n => n.id !== nodeId),
    }));
    setSelectedNode(null);
  };

  const handlePortMouseDown = (e: React.MouseEvent, nodeId: string, portType: "input" | "output", portIndex: number) => {
    e.stopPropagation();
    if (portType === "output") {
      setConnecting({ sourceId: nodeId, sourcePort: String(portIndex) });
    }
  };

  const handlePortMouseUp = (e: React.MouseEvent, nodeId: string, portType: "input" | "output", portIndex: number) => {
    e.stopPropagation();
    if (connecting && portType === "input" && connecting.sourceId !== nodeId) {
      // Create connection
      setPipeline(prev => ({
        ...prev,
        nodes: prev.nodes.map(node => {
          if (node.id === connecting.sourceId) {
            return { ...node, outputs: [...node.outputs, nodeId] };
          }
          if (node.id === nodeId) {
            return { ...node, inputs: [...node.inputs, connecting.sourceId] };
          }
          return node;
        }),
      }));
    }
    setConnecting(null);
  };

  const selectedNodeData = selectedNode
    ? pipeline.nodes.find(n => n.id === selectedNode)
    : null;

  return (
    <div className="flex h-[600px] rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
      {/* Node Palette */}
      <div className="w-48 border-r border-neutral-800 bg-neutral-950 p-3 overflow-y-auto">
        <h3 className="mb-3 font-semibold text-xs text-neutral-400 uppercase tracking-wider">Nodes</h3>
        <div className="space-y-1">
          {Object.entries(nodeTypesConfig).map(([type, config]) => {
            const Icon = ICONS[config.icon];
            const colors = COLOR_CLASSES[config.color];
            return (
              <button
                key={type}
                onClick={() => addNode(type as NodeType)}
                className={cn(
                  "w-full flex items-center gap-2 rounded border px-2 py-1.5 text-left transition-colors",
                  colors.bg, colors.border,
                  "hover:opacity-80"
                )}
              >
                <Icon className={cn("h-4 w-4", colors.text)} />
                <span className={cn("text-xs", colors.text)}>{config.label}</span>
              </button>
            );
          })}
        </div>

        <h3 className="mt-4 mb-3 font-semibold text-xs text-neutral-400 uppercase tracking-wider">Templates</h3>
        <div className="space-y-1">
          {DEFAULT_PIPELINES.map(p => (
            <button
              key={p.id}
              onClick={() => setPipeline(p)}
              className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-left text-xs text-neutral-300 hover:border-neutral-700"
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className="flex-1 relative overflow-hidden bg-neutral-950"
        style={{ cursor: dragging ? "grabbing" : "default" }}
        onMouseMove={(e) => dragging && handleNodeDrag(e, dragging.id)}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={() => setSelectedNode(null)}
      >
        {/* Grid */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: "radial-gradient(circle, #333 1px, transparent 1px)",
            backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
            backgroundPosition: `${pan.x}px ${pan.y}px`,
          }}
        />

        {/* Connections */}
        <svg className="absolute inset-0 pointer-events-none" style={{ transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)` }}>
          {pipeline.nodes.map(node =>
            node.outputs.map((targetId, idx) => {
              const target = pipeline.nodes.find(n => n.id === targetId);
              if (!target) return null;
              const sourceX = node.position.x + 180;
              const sourceY = node.position.y + 25 + idx * 20;
              const targetX = target.position.x;
              const targetY = target.position.y + 25;
              const midX = (sourceX + targetX) / 2;
              return (
                <path
                  key={`${node.id}-${targetId}-${idx}`}
                  d={`M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`}
                  fill="none"
                  stroke="#525252"
                  strokeWidth="2"
                  className="transition-colors"
                />
              );
            })
          )}
        </svg>

        {/* Nodes */}
        <div
          className="absolute inset-0"
          style={{ transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)` }}
        >
          {pipeline.nodes.map(node => {
            const config = nodeTypesConfig[node.type];
            const Icon = ICONS[config.icon];
            const colors = COLOR_CLASSES[config.color];
            const isSelected = selectedNode === node.id;

            return (
              <div
                key={node.id}
                className={cn(
                  "absolute flex items-center gap-2 rounded-lg border px-3 py-2 cursor-grab select-none",
                  colors.bg, colors.border,
                  isSelected && "ring-2 ring-white/30"
                )}
                style={{ left: node.position.x, top: node.position.y }}
                onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                onClick={(e) => { e.stopPropagation(); setSelectedNode(node.id); }}
              >
                {/* Input ports */}
                <div className="absolute -left-2 top-1/2 -translate-y-1/2 flex flex-col gap-1">
                  {config.inputs.map((_, i) => (
                    <div
                      key={i}
                      className="w-3 h-3 rounded-full bg-neutral-600 border border-neutral-500 cursor-crosshair hover:bg-neutral-400"
                      onMouseDown={(e) => handlePortMouseDown(e, node.id, "input", i)}
                      onMouseUp={(e) => handlePortMouseUp(e, node.id, "input", i)}
                    />
                  ))}
                </div>

                <Icon className={cn("h-4 w-4", colors.text)} />
                <span className={cn("text-xs font-medium", colors.text)}>{node.label}</span>

                {/* Output ports */}
                <div className="absolute -right-2 top-1/2 -translate-y-1/2 flex flex-col gap-1">
                  {config.outputs.map((_, i) => (
                    <div
                      key={i}
                      className="w-3 h-3 rounded-full bg-neutral-600 border border-neutral-500 cursor-crosshair hover:bg-neutral-400"
                      onMouseDown={(e) => handlePortMouseDown(e, node.id, "output", i)}
                      onMouseUp={(e) => handlePortMouseUp(e, node.id, "output", i)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Properties Panel */}
      <div className="w-64 border-l border-neutral-800 bg-neutral-950 p-3 overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-xs text-neutral-400 uppercase tracking-wider">Properties</h3>
          <div className="flex gap-1">
            <button onClick={() => setZoom(z => Math.min(2, z + 0.1))} className="p-1 text-neutral-500 hover:text-neutral-300">
              <ZoomIn className="h-4 w-4" />
            </button>
            <button onClick={() => setZoom(z => Math.max(0.5, z - 0.1))} className="p-1 text-neutral-500 hover:text-neutral-300">
              <ZoomOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {selectedNodeData ? (
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-neutral-500 mb-1">Label</label>
              <input
                type="text"
                value={selectedNodeData.label}
                onChange={(e) => setPipeline(prev => ({
                  ...prev,
                  nodes: prev.nodes.map(n =>
                    n.id === selectedNode ? { ...n, label: e.target.value } : n
                  ),
                }))}
                className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-300"
              />
            </div>

            {nodeTypesConfig[selectedNodeData.type].configFields.map(field => (
              <div key={field.name}>
                <label className="block text-xs text-neutral-500 mb-1">{field.name}</label>
                {field.type === "select" ? (
                  <select
                    value={String(selectedNodeData.config[field.name] ?? field.default)}
                    onChange={(e) => setPipeline(prev => ({
                      ...prev,
                      nodes: prev.nodes.map(n =>
                        n.id === selectedNode ? { ...n, config: { ...n.config, [field.name]: e.target.value } } : n
                      ),
                    }))}
                    className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-300"
                  >
                    {field.options?.map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : field.type === "boolean" ? (
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={Boolean(selectedNodeData.config[field.name] ?? field.default)}
                      onChange={(e) => setPipeline(prev => ({
                        ...prev,
                        nodes: prev.nodes.map(n =>
                          n.id === selectedNode ? { ...n, config: { ...n.config, [field.name]: e.target.checked } } : n
                        ),
                      }))}
                      className="rounded border-neutral-600"
                    />
                    <span className="text-xs text-neutral-400">Enabled</span>
                  </label>
                ) : field.type === "number" ? (
                  <input
                    type="number"
                    value={Number(selectedNodeData.config[field.name] ?? field.default)}
                    onChange={(e) => setPipeline(prev => ({
                      ...prev,
                      nodes: prev.nodes.map(n =>
                        n.id === selectedNode ? { ...n, config: { ...n.config, [field.name]: Number(e.target.value) } } : n
                      ),
                    }))}
                    className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-300"
                  />
                ) : (
                  <input
                    type="text"
                    value={String(selectedNodeData.config[field.name] ?? field.default)}
                    onChange={(e) => setPipeline(prev => ({
                      ...prev,
                      nodes: prev.nodes.map(n =>
                        n.id === selectedNode ? { ...n, config: { ...n.config, [field.name]: e.target.value } } : n
                      ),
                    }))}
                    className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-300"
                  />
                )}
              </div>
            ))}

            <button
              onClick={() => deleteNode(selectedNodeData.id)}
              className="w-full flex items-center justify-center gap-2 rounded border border-red-800 bg-red-900/30 px-3 py-2 text-xs text-red-400 hover:bg-red-900/50"
            >
              <Trash2 className="h-3 w-3" />
              Delete Node
            </button>
          </div>
        ) : (
          <p className="text-xs text-neutral-600">Select a node to edit properties</p>
        )}

        {/* Actions */}
        <div className="mt-4 pt-4 border-t border-neutral-800 space-y-2">
          <button
            onClick={() => onSave?.(pipeline)}
            className="w-full flex items-center justify-center gap-2 rounded bg-violet-800 px-3 py-2 text-xs font-medium text-violet-100 hover:bg-violet-700"
          >
            <Save className="h-3 w-3" />
            Save Pipeline
          </button>
          <button
            onClick={() => onRun?.(pipeline)}
            className="w-full flex items-center justify-center gap-2 rounded bg-emerald-800 px-3 py-2 text-xs font-medium text-emerald-100 hover:bg-emerald-700"
          >
            <Play className="h-3 w-3" />
            Run Pipeline
          </button>
        </div>
      </div>
    </div>
  );
}
