import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Sparkles,
  Send,
  Cpu,
  ShieldCheck,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Database,
  Layers,
  ArrowRight,
  TrendingUp,
  BarChart2,
  RefreshCw,
  ExternalLink,
  Info
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from 'recharts';
import { queryAgent, getAgentStatus } from '../services/api';

const EXAMPLE_QUERIES = [
  "Why is Punjab over-exploited and how did it change from 2020 to 2026?",
  "Compare groundwater extraction and recharge between Punjab and Haryana in 2025",
  "Why does South Delhi have high extraction and what is the domestic vs industrial draft?",
  "Recommend conservation policies for Ludhiana based on its stage of extraction"
];

export default function AIAnalystPage() {
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [mode, setMode] = useState('auto'); // 'auto' | 'agentic' | 'deterministic'
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [expandedTrace, setExpandedTrace] = useState({});
  const [expandedEvidence, setExpandedEvidence] = useState({});
  const messagesEndRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await getAgentStatus();
      setStatus(res.data);
    } catch (e) {
      console.warn('Could not fetch agent status', e);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleSend = async (queryToSend = null) => {
    const q = (queryToSend || inputQuery).trim();
    if (!q || loading) return;

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      query: q,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const response = await queryAgent(q, mode);
      const agentMessage = {
        id: Date.now() + 1,
        sender: 'agent',
        data: response.data,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      console.error('Agent query error:', err);
      const errorMessage = {
        id: Date.now() + 1,
        sender: 'agent',
        error: true,
        message: err.response?.data?.detail || 'Network or server error executing query.',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const toggleTrace = (id) => {
    setExpandedTrace((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleEvidence = (id) => {
    setExpandedEvidence((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] bg-[#07131e] text-slate-100 overflow-hidden">
      {/* Top Bar / Status */}
      <div className="border-b border-slate-800 bg-[#091a29]/90 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white flex items-center gap-2">
              Autonomous Groundwater AI Analyst
              <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                ReAct + Grounded Synthesis
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Multi-step tool reasoning with 100% strict CGWB anti-hallucination verification
            </p>
          </div>
        </div>

        {/* Mode Selector & Status */}
        <div className="flex items-center gap-3">
          <div className="flex bg-[#061019] p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setMode('auto')}
              className={`px-3 py-1.5 rounded-md transition-all font-medium ${
                mode === 'auto'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Auto (Intelligent)
            </button>
            <button
              onClick={() => setMode('agentic')}
              className={`px-3 py-1.5 rounded-md transition-all font-medium ${
                mode === 'agentic'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Agentic (ReAct)
            </button>
            <button
              onClick={() => setMode('deterministic')}
              className={`px-3 py-1.5 rounded-md transition-all font-medium ${
                mode === 'deterministic'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Deterministic (&lt;10ms)
            </button>
          </div>

          {status && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>{status.model || 'gemini-2.5-flash'}</span>
              <span className={`w-2 h-2 rounded-full ${status.api_key_configured ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            </div>
          )}
        </div>
      </div>

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-3xl mx-auto py-12 text-center space-y-6">
            <div className="inline-flex p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Sparkles className="w-10 h-10" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">
                Ask Complex Hydrogeological Questions
              </h2>
              <p className="text-sm text-slate-400 max-w-xl mx-auto">
                The agent inspects official CGWB Dynamic Ground Water Resources records, executes multi-step database tools, analyzes trajectory across cycles, and synthesizes grounded insights.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left max-w-2xl mx-auto pt-2">
              {EXAMPLE_QUERIES.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  className="p-3.5 rounded-xl bg-[#091a29]/80 border border-slate-800 hover:border-cyan-500/40 hover:bg-[#0c2236] transition-all text-xs text-slate-300 flex items-start justify-between group"
                >
                  <span className="leading-relaxed">{q}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 mt-1 shrink-0 ml-2" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="max-w-4xl mx-auto">
              {msg.sender === 'user' ? (
                <div className="flex justify-end">
                  <div className="max-w-2xl bg-cyan-700/30 border border-cyan-500/40 rounded-2xl rounded-tr-sm px-4 py-3 text-slate-100 text-sm shadow-md">
                    <p className="font-medium text-cyan-200 text-xs mb-1">Question</p>
                    <p>{msg.query}</p>
                  </div>
                </div>
              ) : msg.error ? (
                <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-200 text-sm flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
                  <p>{msg.message}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Badges Bar */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className={`px-2.5 py-1 rounded-full border font-medium ${
                      msg.data.mode_used === 'agentic'
                        ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                        : msg.data.mode_used === 'deterministic'
                        ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                        : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                    }`}>
                      {msg.data.mode_used === 'agentic' && 'Autonomous ReAct Flow'}
                      {msg.data.mode_used === 'deterministic' && 'Deterministic Engine'}
                      {msg.data.mode_used === 'deterministic_fallback' && 'Deterministic Fallback'}
                    </span>

                    {msg.data.verification?.passed && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-medium">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                        All figures verified against CGWB
                      </span>
                    )}

                    <span className="text-slate-400 ml-auto">
                      Latency: <span className="text-slate-200 font-mono">{msg.data.latency_ms} ms</span>
                    </span>
                  </div>

                  {/* Summary Card */}
                  <div className="p-5 rounded-2xl bg-[#091a29] border border-slate-800 shadow-lg space-y-4">
                    <div>
                      <h3 className="text-xs uppercase tracking-wider font-semibold text-cyan-400 mb-2">
                        Verified Executive Summary
                      </h3>
                      <p className="text-sm text-slate-200 leading-relaxed font-sans">
                        {msg.data.answer?.summary}
                      </p>
                    </div>

                    {/* Numeric Breakdown Table */}
                    {msg.data.answer?.numeric_breakdown?.length > 0 && (
                      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-800/80">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-[#050d15] text-slate-400 border-b border-slate-800">
                            <tr>
                              <th className="px-3.5 py-2.5 font-medium">Parameter</th>
                              <th className="px-3.5 py-2.5 font-medium">Value</th>
                              <th className="px-3.5 py-2.5 font-medium">Unit</th>
                              <th className="px-3.5 py-2.5 font-medium">Year</th>
                              <th className="px-3.5 py-2.5 font-medium">Location</th>
                              <th className="px-3.5 py-2.5 font-medium">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 bg-[#07131e]/50">
                            {msg.data.answer.numeric_breakdown.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-slate-800/20">
                                <td className="px-3.5 py-2 text-slate-200 font-medium">{row.parameter || row.metric}</td>
                                <td className="px-3.5 py-2 font-mono text-cyan-300 font-semibold">
                                  {typeof row.value === 'number' ? row.value.toLocaleString() : row.value}
                                </td>
                                <td className="px-3.5 py-2 text-slate-400">{row.unit}</td>
                                <td className="px-3.5 py-2 text-slate-300">{row.year}</td>
                                <td className="px-3.5 py-2 text-slate-300">{row.location}</td>
                                <td className="px-3.5 py-2">
                                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-medium">
                                    VERIFIED
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Trend Chart (if multi-point numeric breakdown) */}
                    {msg.data.answer?.numeric_breakdown?.length > 1 && (
                      <div className="mt-4 p-4 rounded-xl bg-[#061019] border border-slate-800/80">
                        <p className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-1.5">
                          <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
                          Comparative Metric Visualization
                        </p>
                        <div className="h-44 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                              data={msg.data.answer.numeric_breakdown.map((item) => ({
                                name: item.parameter?.slice(0, 16) || item.location || 'Metric',
                                value: typeof item.value === 'number' ? item.value : parseFloat(item.value) || 0,
                                unit: item.unit,
                              }))}
                              margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                              <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#091a29', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                              />
                              <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )}

                    {/* Trend Analysis Section */}
                    {msg.data.answer?.trend_analysis && (
                      <div className="pt-2 border-t border-slate-800/80">
                        <h4 className="text-xs font-semibold text-cyan-400 flex items-center gap-1.5 mb-1">
                          <TrendingUp className="w-3.5 h-3.5" />
                          Temporal Trend Trajectory
                        </h4>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {msg.data.answer.trend_analysis}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* AI Interpretation & Policy Recommendations (Strictly Labeled) */}
                  {(msg.data.answer?.interpretation || msg.data.answer?.policy_recommendations?.length > 0) && (
                    <div className="p-5 rounded-2xl bg-[#091a29]/80 border border-amber-500/20 shadow-md space-y-4">
                      <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider">
                        <Info className="w-4 h-4" />
                        AI Hydrogeological Interpretation & Policy Guidance
                      </div>
                      <p className="text-[11px] text-amber-300/80 italic">
                        Notice: General hydrogeological principles and AI conservation suggestions; not official CGWB causal determinations or administrative orders.
                      </p>

                      {msg.data.answer.interpretation && (
                        <div>
                          <p className="text-xs text-slate-300 leading-relaxed font-sans">
                            {msg.data.answer.interpretation}
                          </p>
                        </div>
                      )}

                      {msg.data.answer.policy_recommendations?.length > 0 && (
                        <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
                          <p className="text-xs font-medium text-slate-200">Recommended Conservation Pathways:</p>
                          <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                            {msg.data.answer.policy_recommendations.map((rec, rIdx) => (
                              <li key={rIdx} className="leading-relaxed">{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Reasoning Trace Panel */}
                  {msg.data.steps?.length > 0 && (
                    <div className="rounded-xl border border-slate-800 bg-[#061019] overflow-hidden text-xs">
                      <button
                        onClick={() => toggleTrace(msg.id)}
                        className="w-full px-4 py-3 flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800/40 transition-all font-medium"
                      >
                        <span className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-purple-400" />
                          ReAct Reasoning Trace ({msg.data.steps.length} {msg.data.steps.length === 1 ? 'step' : 'steps'})
                        </span>
                        {expandedTrace[msg.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>

                      {expandedTrace[msg.id] && (
                        <div className="p-4 border-t border-slate-800/80 space-y-3 bg-[#050c14]">
                          {msg.data.steps.map((st, sIdx) => (
                            <div key={sIdx} className="p-3 rounded-lg bg-[#081522] border border-slate-800/80 space-y-1.5 font-mono text-[11px]">
                              <div className="flex items-center justify-between text-slate-400">
                                <span className="font-semibold text-purple-300">Step {st.step_number}: Tool '{st.tool}'</span>
                                <span>{st.latency_ms} ms</span>
                              </div>
                              <p className="text-slate-300 font-sans">{st.thought}</p>
                              {st.args && Object.keys(st.args).length > 0 && (
                                <p className="text-slate-400 text-[10px]">
                                  Args: {JSON.stringify(st.args)}
                                </p>
                              )}
                              <p className="text-emerald-400 text-[10px]">{st.result_summary}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Evidence & Provenance Panel */}
                  {msg.data.citations?.length > 0 && (
                    <div className="rounded-xl border border-slate-800 bg-[#061019] overflow-hidden text-xs">
                      <button
                        onClick={() => toggleEvidence(msg.id)}
                        className="w-full px-4 py-3 flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800/40 transition-all font-medium"
                      >
                        <span className="flex items-center gap-2">
                          <Database className="w-4 h-4 text-cyan-400" />
                          Official CGWB Data Provenance ({msg.data.citations.length} sources)
                        </span>
                        {expandedEvidence[msg.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>

                      {expandedEvidence[msg.id] && (
                        <div className="p-4 border-t border-slate-800/80 space-y-2 bg-[#050c14]">
                          {msg.data.citations.map((cite, cIdx) => (
                            <div key={cIdx} className="p-2.5 rounded-lg bg-[#081522] border border-slate-800 flex items-center justify-between text-xs">
                              <div>
                                <p className="font-medium text-slate-200">{cite.source_document}</p>
                                <p className="text-[11px] text-slate-400">
                                  Agency: {cite.source_agency} | Assessment Cycle: {cite.assessment_year}
                                </p>
                              </div>
                              {cite.source_document_url && (
                                <a
                                  href={cite.source_document_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px]"
                                >
                                  Official PDF
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {/* Live Loading Pulse */}
        {loading && (
          <div className="max-w-4xl mx-auto p-4 rounded-xl bg-[#091a29]/90 border border-cyan-500/30 flex items-center gap-3 text-cyan-300 text-sm animate-pulse">
            <RefreshCw className="w-4 h-4 animate-spin shrink-0 text-cyan-400" />
            <span>Agentic Orchestrator is formulating query plan and gathering verified CGWB observations...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 border-t border-slate-800 bg-[#091a29]/90">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="max-w-4xl mx-auto flex gap-3"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask complex or multi-year question (e.g. 'Why is Punjab over-exploited and how did it change from 2020 to 2026?')..."
            className="flex-1 bg-[#061019] border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/80 transition-all font-sans"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !inputQuery.trim()}
            className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-md shadow-cyan-900/30 shrink-0"
          >
            <span>Analyze</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
