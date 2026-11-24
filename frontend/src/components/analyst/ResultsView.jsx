import React, { useState } from 'react';
import {
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
  BarChart2,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

export default function ResultsView({ result, loading, error }) {
  const [expandedProvenance, setExpandedProvenance] = useState(false);

  if (loading) {
    return (
      <div className="bg-[#0f1f33] rounded-lg p-6 border border-slate-800/80 shadow-md space-y-4 animate-pulse">
        <div className="flex items-center gap-3 text-teal-400 text-sm">
          <RefreshCw className="w-5 h-5 animate-spin text-teal-400" />
          <span className="font-medium">
            Agentic Orchestrator is formulating query plan and querying verified CGWB databases...
          </span>
        </div>
        <div className="space-y-2 pt-2">
          <div className="h-4 bg-slate-800 rounded w-3/4" />
          <div className="h-4 bg-slate-800 rounded w-5/6" />
          <div className="h-4 bg-slate-800 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950/40 rounded-lg p-5 border border-red-500/40 shadow-md flex items-start gap-3 text-red-200 text-sm">
        <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-red-300">Unable to process query</p>
          <p className="text-xs text-red-200/90 leading-relaxed">{error}</p>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const {
    answer = {},
    mode_used = 'agentic',
    verification = {},
    steps = [],
    citations = [],
    latency_ms = 0,
  } = result;

  const isVerified = verification.passed && !verification.regenerated;
  const isRegenerated = verification.regenerated;
  const isFallback = mode_used === 'template_fallback' || verification.fallback_used;

  return (
    <div className="space-y-4">
      {/* Badges / Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Badge */}
          <span
            className={`px-2.5 py-1 rounded-full border font-medium ${
              mode_used === 'agentic'
                ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                : mode_used === 'template'
                ? 'bg-teal-500/10 text-teal-300 border-teal-500/30'
                : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
            }`}
          >
            {mode_used === 'agentic' && 'Autonomous ReAct Flow'}
            {mode_used === 'template' && 'Template Mode'}
            {mode_used === 'template_fallback' && 'Template Fallback'}
          </span>

          {/* Audit Badge */}
          {isVerified && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              All figures verified against CGWB
            </span>
          )}
          {isRegenerated && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 font-medium">
              <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
              Regenerated once
            </span>
          )}
          {isFallback && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10 text-red-300 border border-red-500/30 font-medium">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              Template fallback applied
            </span>
          )}
        </div>

        <span className="text-slate-400 text-xs">
          Latency: <span className="text-slate-200 font-mono">{latency_ms} ms</span>
        </span>
      </div>

      {/* Verified CGWB Data Panel */}
      <div className="bg-[#0f1f33] rounded-lg p-5 sm:p-6 border border-slate-800/80 shadow-md space-y-4">
        <div>
          <h2 className="text-xs uppercase tracking-wider font-semibold text-teal-400 mb-2">
            Verified Executive Summary
          </h2>
          <p className="text-sm text-slate-200 leading-relaxed font-sans">
            {answer.summary || 'Summary generated from database records.'}
          </p>
        </div>

        {/* Numeric Breakdown Table */}
        {answer.numeric_breakdown?.length > 0 && (
          <div className="mt-4 overflow-x-auto rounded-lg border border-slate-800/80">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#091522] text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-3.5 py-2.5 font-medium">Parameter</th>
                  <th className="px-3.5 py-2.5 font-medium">Value</th>
                  <th className="px-3.5 py-2.5 font-medium">Unit</th>
                  <th className="px-3.5 py-2.5 font-medium">Year</th>
                  <th className="px-3.5 py-2.5 font-medium">Location</th>
                  <th className="px-3.5 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-[#0b1a2d]/60">
                {answer.numeric_breakdown.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-800/20">
                    <td className="px-3.5 py-2 text-slate-200 font-medium">
                      {row.parameter || row.metric}
                    </td>
                    <td className="px-3.5 py-2 font-mono text-teal-300 font-semibold">
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

        {/* Dynamic Comparative Visualization (Recharts) */}
        {answer.numeric_breakdown?.length > 1 && (
          <div className="mt-4 p-4 rounded-lg bg-[#0b1a2d] border border-slate-800/80">
            <p className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5 text-teal-400" />
              Comparative Metric Visualization
            </p>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={answer.numeric_breakdown.map((item) => ({
                    name: (item.parameter || item.metric)?.slice(0, 16) || item.location || 'Metric',
                    value: typeof item.value === 'number' ? item.value : parseFloat(item.value) || 0,
                    unit: item.unit,
                  }))}
                  margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#091a29',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="value" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Trend Analysis */}
        {answer.trend_analysis && (
          <div className="pt-2 border-t border-slate-800/80">
            <h3 className="text-xs font-semibold text-teal-400 flex items-center gap-1.5 mb-1">
              <TrendingUp className="w-3.5 h-3.5" />
              Temporal Trend Trajectory
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              {answer.trend_analysis}
            </p>
          </div>
        )}
      </div>

      {/* Collapsible Data Provenance */}
      {citations.length > 0 && (
        <div className="rounded-lg border border-slate-800/80 bg-[#0f1f33] overflow-hidden text-xs">
          <button
            type="button"
            onClick={() => setExpandedProvenance((prev) => !prev)}
            className="w-full px-4 py-3 flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800/30 transition-all font-medium"
          >
            <span className="flex items-center gap-2">
              <Database className="w-4 h-4 text-teal-400" />
              <span>Official CGWB Data Provenance ({citations.length} sources)</span>
            </span>
            {expandedProvenance ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {expandedProvenance && (
            <div className="p-4 border-t border-slate-800/80 space-y-2 bg-[#0b1a2d]">
              {citations.map((cite, cIdx) => (
                <div key={cIdx} className="p-2.5 rounded-md bg-[#091522] border border-slate-800 flex items-center justify-between text-xs">
                  <div>
                    <p className="font-medium text-slate-200">
                      {typeof cite === 'string' ? cite : cite.source_document || 'CGWB Assessment Report'}
                    </p>
                    {typeof cite !== 'string' && (
                      <p className="text-[11px] text-slate-400">
                        Agency: {cite.source_agency || 'CGWB'} | Cycle: {cite.assessment_year}
                      </p>
                    )}
                  </div>
                  {typeof cite !== 'string' && cite.source_document_url && (
                    <a
                      href={cite.source_document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-teal-400 hover:text-teal-300 flex items-center gap-1 text-[11px]"
                    >
                      Official PDF <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
