import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import {
    Play, Split, Wrench, Globe, Database,
    Link, ScrollText, Settings2, Webhook, Workflow,
    Target, Repeat, BarChart2, Save, Zap, ShieldAlert,
    Clock, SquarePen, Plug, Activity
} from 'lucide-react';

const NodeIcon = ({ type }) => {
    switch (type) {
        // Basic
        case 'integration':
        case 'integration_task': return <Link size={16} className="text-blue-400" />;
        case 'script': return <ScrollText size={16} className="text-yellow-400" />;
        case 'http':
        case 'http_request': return <Globe size={16} className="text-green-400" />;
        case 'parameter': return <Settings2 size={16} className="text-gray-400" />;
        case 'webhook': return <Webhook size={16} className="text-pink-400" />;
        case 'workflow': return <Workflow size={16} className="text-indigo-400" />;

        // Control
        case 'condition': return <Split size={16} className="text-orange-400" />;
        case 'switch': return <Target size={16} className="text-red-400" />;
        case 'loop': return <Repeat size={16} className="text-blue-300" />;

        // Data
        case 'variable': return <BarChart2 size={16} className="text-purple-400" />;
        case 'cache': return <Save size={16} className="text-cyan-400" />;

        // Advanced
        case 'parallel': return <Zap size={16} className="text-yellow-300" />;
        case 'try_catch': return <ShieldAlert size={16} className="text-red-500" />;
        case 'delay': return <Clock size={16} className="text-gray-300" />;
        case 'log': return <SquarePen size={16} className="text-white" />;

        // Integration
        case 'mcp_server': return <Plug size={16} className="text-green-300" />;

        // Fallback / Generic
        case 'trigger': return <Play size={16} className="text-green-500" />;
        case 'action': return <Activity size={16} className="text-blue-500" />;
        default: return <Wrench size={16} className="text-gray-500" />;
    }
};

const NodeShape = ({ type, width, height }) => {
    // Colors
    const fill = "#1f2937"; // gray-800
    let stroke = "white";
    let strokeWidth = 2;

    if (['trigger', 'webhook'].includes(type)) stroke = "#22c55e"; // green-500
    if (['condition', 'switch'].includes(type)) stroke = "#f97316"; // orange-500
    if (['log'].includes(type)) stroke = "#a855f7"; // purple-500
    if (['action', 'http_request', 'script'].includes(type)) stroke = "#60a5fa"; // blue-400

    // Shapes
    if (['trigger', 'webhook'].includes(type)) {
        // Pill / Rounded Rect
        const r = height / 2;
        return <rect x="2" y="2" width={width - 4} height={height - 4} rx={r} ry={r} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    }
    if (['condition', 'switch'].includes(type)) {
        // Diamond
        const halfW = width / 2;
        const halfH = height / 2;
        // Points: Top, Right, Bottom, Left
        const points = `${halfW},2 ${width - 2},${halfH} ${halfW},${height - 2} 2,${halfH}`;
        return <polygon points={points} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    }
    if (['log'].includes(type)) {
        // Document (wavy bottom or just clipped corner)
        // Simple path for document with wavy bottom
        const w = width - 4;
        const h = height - 4;
        const wave = `Q ${w * 0.25} ${h - 10}, ${w * 0.5} ${h} T ${w} ${h - 10}`;
        const d = `M 2,2 L ${w},2 L ${w},${h - 10} ${wave} L 2,${h - 10} Z`;
        // Fallback to simple Rect with wave visual if path is complex
        // Let's use a simpler "Document" symbol: Rect with wavy bottom line
        return (
            <path d={`M 2,2 L ${width - 2},2 L ${width - 2},${height - 15} Q ${width / 2},${height + 5} 2,${height - 15} Z`} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
        );
    }

    // Default: Rectangle (Process)
    return <rect x="2" y="2" width={width - 4} height={height - 4} rx="4" ry="4" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
};

const CustomNode = ({ data }) => {
    const { label, nodeType, config } = data;

    // Standardize dimensions per shape type for a clean production look
    let width = 240;
    let height = 110;

    // Diamonds need more aspect ratio breathing room
    if (['condition', 'switch'].includes(nodeType)) {
        width = 250;
        height = 160;
    }

    return (
        <div style={{ width, height }} className="relative filter drop-shadow-2xl text-white font-sans transition-all duration-300 hover:scale-[1.02] group">
            {/* SVG Background Layer - No default background, perfectly transparent around shape */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <svg width={width} height={height} className="overflow-visible">
                    <NodeShape type={nodeType} width={width} height={height} />
                </svg>
            </div>

            {/* Content Layer - Absolutely positioned to overlay the shape perfectly */}
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-6 text-center pointer-events-none select-none">
                <div className="mb-1.5 p-1 bg-black/30 rounded-full shrink-0 border border-white/5">
                    <NodeIcon type={nodeType} />
                </div>

                <div className="font-extrabold text-[13px] leading-tight break-words w-full max-h-[48px] overflow-hidden text-ellipsis px-2 text-gray-100">
                    {label}
                </div>

                <div className="text-[9px] opacity-40 uppercase tracking-[0.2em] font-mono mt-1 shrink-0">
                    {data.integration_type_name || nodeType?.replace('_', ' ')}
                </div>

                {/* Minimal Config / Params display */}
                {!['trigger', 'webhook', 'condition', 'switch'].includes(nodeType) && (
                    <div className="mt-2 text-[8px] bg-black/40 px-2 py-1 rounded border border-white/10 max-w-full truncate shrink-0 text-gray-400 font-mono">
                        {['integration', 'integration_task'].includes(nodeType) && (data.task_display_name || data.task) ? (
                            <span className="text-blue-300">{data.task_display_name || data.task}</span>
                        ) : ['http', 'http_request'].includes(nodeType) && data.config?.url ? (
                            <span className="text-green-300">{data.config.url}</span>
                        ) : nodeType === 'script' && (data.code || data.config?.code) ? (
                            <span className="text-yellow-200">{(data.code || data.config.code).slice(0, 30)}...</span>
                        ) : (
                            Object.values(data.config || data.params || {}).join(', ').slice(0, 30)
                        )}
                    </div>
                )}
            </div>

            {/* Handles - Positioned at exact geometric center-points for perfect edge alignment */}
            <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-white/80 !-ml-1.5 border-2 border-gray-900 !transition-transform group-hover:!scale-125" />

            {['condition', 'switch'].includes(nodeType) ? (
                <>
                    {/* Top = True Branch */}
                    <Handle type="source" id="true" position={Position.Top} className="!bg-green-500 !w-3 !h-3 !-mt-1.5 border-2 border-gray-900 !transition-all group-hover:!scale-125" />
                    {/* Bottom = False Branch */}
                    <Handle type="source" id="false" position={Position.Bottom} className="!bg-red-500 !w-3 !h-3 !-mb-1.5 border-2 border-gray-900 !transition-all group-hover:!scale-125" />
                    {/* Right Handle for Fallback or Sequence */}
                    <Handle type="source" position={Position.Right} className="!bg-white/80 !w-2.5 !h-2.5 !-mr-1.5 border-2 border-gray-900" />
                </>
            ) : (
                <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-white/80 !-mr-1.5 border-2 border-gray-900 !transition-transform group-hover:!scale-125" />
            )}
        </div>
    );
};

export default memo(CustomNode);
