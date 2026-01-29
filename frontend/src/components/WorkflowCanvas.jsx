import React, { useCallback, useEffect } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, addEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import CustomNode from './CustomNode';

const nodeTypes = {
    trigger: CustomNode,
    action: CustomNode,
    condition: CustomNode,
    utility: CustomNode,
    control: CustomNode,
    http: CustomNode,
    integration: CustomNode,
    script: CustomNode,
    log: CustomNode,
    webhook: CustomNode,
    default: CustomNode
};

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const isHorizontal = direction === 'LR';
    dagreGraph.setGraph({
        rankdir: direction,
        ranksep: 200, // Even more horizontal spacing for diamonds
        nodesep: 100  // More vertical spacing
    });

    nodes.forEach((node) => {
        // Diamonds and Rectangles have different footprints
        const isDiamond = node.data?.nodeType === 'condition' || node.type === 'control';
        dagreGraph.setNode(node.id, { width: isDiamond ? 300 : 250, height: isDiamond ? 150 : 120 });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        const isDiamond = node.data?.nodeType === 'condition' || node.type === 'control';
        const w = isDiamond ? 300 : 250;
        const h = isDiamond ? 150 : 120;

        return {
            ...node,
            targetPosition: isHorizontal ? 'left' : 'top',
            sourcePosition: isHorizontal ? 'right' : 'bottom',
            position: {
                x: nodeWithPosition.x - w / 2,
                y: nodeWithPosition.y - h / 2,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};


const WorkflowCanvas = ({ graphData }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    useEffect(() => {
        if (graphData) {
            // Support both internal simple format and company nested format
            let rawNodes = [];
            let rawEdges = [];

            if (graphData.workflows && graphData.workflows[0]) {
                const w = graphData.workflows[0].workflow_data;
                rawNodes = w.nodes || [];
                rawEdges = w.connections || [];
            } else {
                rawNodes = graphData.nodes || [];
                rawEdges = graphData.edges || [];
            }

            // Normalize nodes for React Flow
            const normalizedNodes = rawNodes.map(n => {
                const nodeType = n.type || 'default';
                const mappedType = nodeTypes[nodeType] ? nodeType : 'default';

                return {
                    id: String(n.id),
                    type: mappedType,
                    data: {
                        label: n.label || n.data?.label || 'Untitled',
                        nodeType: n.type || n.data?.nodeType,
                        config: n.config || n.data?.config || {},
                        params: n.params || {},
                        integration_type_name: n.integration_type_name,
                        task: n.task,
                        task_display_name: n.task_display_name
                    },
                    position: n.position || { x: 0, y: 0 }
                };
            });

            // Normalize edges (source/target or from/to)
            const processedEdges = rawEdges.map((edge, idx) => {
                const source = String(edge.source || edge.from);
                const target = String(edge.target || edge.to);
                const sourceNode = normalizedNodes.find(n => n.id === source);
                const isDecision = sourceNode?.data?.nodeType === 'condition' || sourceNode?.type === 'control';

                let sourceHandle = edge.sourceHandle;
                if (isDecision && edge.label) {
                    const labelLower = String(edge.label).toLowerCase();
                    if (labelLower === 'true') sourceHandle = 'true';
                    if (labelLower === 'false') sourceHandle = 'false';
                }
                // Also support condition block mapping if sourceHandle is missing but it's a condition
                if (isDecision && !sourceHandle && edge.condition?.value) {
                    sourceHandle = edge.condition.value;
                }

                return {
                    id: edge.id || `e-${idx}`,
                    source,
                    target,
                    sourceHandle,
                    label: edge.label || (edge.condition?.value ? String(edge.condition.value).toUpperCase() : '')
                };
            });

            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
                normalizedNodes,
                processedEdges
            );

            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        }
    }, [graphData, setNodes, setEdges]);

    const onConnect = useCallback(
        (params) => setEdges((eds) => addEdge(params, eds)),
        [setEdges],
    );

    return (
        <div style={{ height: '600px', width: '100%' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes} // Pass Custom Nodes
                fitView
                className="bg-black/20"
            >
                <Background color="#333" gap={20} />
                <Controls className="!bg-[#131315] !border-gray-800 !fill-gray-400" />
            </ReactFlow>
        </div>
    );
};

export default WorkflowCanvas;
