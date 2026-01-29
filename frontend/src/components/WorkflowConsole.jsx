import React, { useState, useRef, useEffect } from 'react';
import WorkflowCanvas from './WorkflowCanvas';

const WorkflowConsole = () => {
    const [prompt, setPrompt] = useState('');
    const [status, setStatus] = useState('idle'); // idle, planning, executing, success, error
    const [messages, setMessages] = useState([]);
    const [graphData, setGraphData] = useState(null);
    const [executionLogs, setExecutionLogs] = useState([]);
    const bottomRef = useRef(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        // Reset state for new run
        setStatus('planning');
        setMessages(prev => [...prev, { type: 'user', content: prompt }]);
        setGraphData(null);
        setExecutionLogs([]);
        const currentPrompt = prompt;
        setPrompt('');

        try {
            // Call Backend API
            const response = await fetch('http://localhost:5001/api/run_workflow', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: currentPrompt })
            });

            if (!response.ok) throw new Error('API Request Failed');

            const data = await response.json();

            // Updates based on response
            if (data.results && data.results.graph) {
                setGraphData(data.results.graph);

                // Simulate "streaming" the logs for effect
                setStatus('executing');
                const rawMessages = data.messages || [];

                // Process messages to separate plan from execution logs
                const newLogs = rawMessages.map(msg => ({
                    type: 'agent',
                    content: typeof msg === 'string' ? msg : JSON.stringify(msg),
                    timestamp: new Date().toLocaleTimeString()
                }));

                setExecutionLogs(newLogs);
                setStatus('success');
            } else {
                setStatus('error');
                setExecutionLogs([{ type: 'error', content: 'Workflow failed or no graph returned.' }]);
            }

        } catch (err) {
            console.error(err);
            setStatus('error');
            setExecutionLogs(prev => [...prev, { type: 'error', content: `Connection Error: ${err.message}` }]);
        }
    };

    // Auto-scroll to bottom
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [executionLogs, status]);

    const loadSampleGraph = () => {
        console.log("Loading Sample Graph...");
        setGraphData({
            nodes: [
                { id: '1', type: 'trigger', data: { label: 'Start Trigger', nodeType: 'webhook' }, position: { x: 0, y: 0 } },
                { id: '2', type: 'action', data: { label: 'Fetch Data', nodeType: 'http_request' }, position: { x: 200, y: 0 } },
                { id: '3', type: 'utility', data: { label: 'Log Info', nodeType: 'log' }, position: { x: 400, y: 0 } }
            ],
            edges: [
                { id: 'e1-2', source: '1', target: '2' },
                { id: 'e2-3', source: '2', target: '3' }
            ]
        });
        setStatus('success');
    };

    const downloadJson = () => {
        if (!graphData) return;
        const blob = new Blob([JSON.stringify(graphData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `workflow-${new Date().getTime()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="w-full max-w-7xl mx-auto p-4 flex flex-col gap-6 h-full">
            {/* Header */}
            <div className="glass-panel p-6 flex justify-between items-center animate-fade-in flex-shrink-0">
                <div>
                    <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400 glow-text">
                        Agentic Workflow Builder
                    </h1>
                    <p className="text-sm text-gray-400">Powered by LangGraph & Bedrock</p>
                </div>
                <div className="flex gap-3 items-center">
                    {graphData && (
                        <button onClick={downloadJson} className="flex items-center gap-2 text-xs px-3 py-1.5 bg-indigo-600 border border-indigo-400 rounded-md text-white hover:bg-indigo-500 hover:scale-105 transition-all shadow-lg active:scale-95 cursor-pointer">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" x2="12" y1="15" y2="3" /></svg>
                            Download JSON
                        </button>
                    )}
                    <button onClick={loadSampleGraph} className="text-xs px-3 py-1.5 bg-gray-800 border border-gray-600 rounded-md text-gray-300 hover:bg-gray-700 transition cursor-pointer">
                        Debug: Load Sample
                    </button>
                    <div className={`px-3 py-1.5 rounded-full text-xs font-mono border ${status === 'idle' ? 'border-gray-600 text-gray-400' :
                        status === 'success' ? 'border-green-500 text-green-400 bg-green-900/20' :
                            status === 'error' ? 'border-red-500 text-red-400 bg-red-900/20' :
                                'border-indigo-500 text-indigo-400 bg-indigo-900/20 animate-pulse'
                        }`}>
                        STATUS: {status.toUpperCase()}
                    </div>
                </div>
            </div>

            <div className="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
                {/* Left Panel: Plan Visualization / Graph */}
                <div className="glass-panel p-0 flex-[2] relative h-[600px] overflow-hidden">
                    <div className="absolute top-0 left-0 p-4 z-10 pointer-events-none">
                        <h2 className="text-lg font-semibold text-gray-200 shadow-sm bg-black/50 rounded px-2">
                            Workflow Visualizer
                        </h2>
                    </div>

                    {!graphData && status === 'idle' && (
                        <div className="flex items-center justify-center h-full text-gray-600 italic">
                            Waiting for instructions...
                        </div>
                    )}

                    {!graphData && status === 'planning' && (
                        <div className="flex items-center justify-center h-full text-indigo-400 animate-pulse">
                            Generative AI Agent is designing the workflow graph...
                        </div>
                    )}

                    {/* Render Canvas if graph data exists */}
                    {graphData && (
                        <div className="absolute inset-0 w-full h-full bg-[#1e1e20]">
                            <WorkflowCanvas graphData={graphData} />
                        </div>
                    )}
                </div>

                {/* Right Panel: Execution Logs */}
                <div className="glass-panel p-6 flex-1 flex flex-col gap-4 overflow-hidden min-w-[300px] h-[600px]">
                    <h2 className="text-lg font-semibold text-gray-200 border-b border-gray-800 pb-2">
                        Activity Log
                    </h2>

                    <div className="flex-1 overflow-y-auto space-y-2 font-mono text-sm custom-scrollbar bg-black/30 p-4 rounded-lg">
                        {messages.map((msg, i) => (
                            <div key={`msg-${i}`} className="text-indigo-300 border-b border-gray-800 pb-2 mb-2">
                                <span className="text-gray-500 text-xs">USER &gt;</span> {msg.content}
                            </div>
                        ))}

                        {executionLogs.map((log, i) => (
                            <div key={`log-${i}`} className={`animate-fade-in ${log.type === 'error' ? 'text-red-400' : 'text-green-400'}`}>
                                <span className="text-gray-600 text-xs">[{log.timestamp}]</span> {log.type.toUpperCase()}:
                                <div className="pl-4 text-gray-300 whitespace-pre-wrap">{log.content}</div>
                            </div>
                        ))}

                        <div ref={bottomRef} />
                    </div>
                </div>
            </div>

            {/* Input Area */}
            <form onSubmit={handleSubmit} className="glass-panel p-4 flex gap-4 mt-auto flex-shrink-0">
                <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe a workflow (e.g., 'Restart database if CPU > 80%')..."
                    className="input-field flex-1"
                    disabled={status === 'planning' || status === 'executing'}
                />
                <button
                    type="submit"
                    disabled={status === 'planning' || status === 'executing' || !prompt.trim()}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed hidden md:block" // Hide on small screens if needed
                >
                    Generate Workflow
                </button>
            </form>
        </div>
    );
};

export default WorkflowConsole;
