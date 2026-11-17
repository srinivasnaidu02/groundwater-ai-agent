import React from 'react';
import {
  Info,
  ShieldCheck,
  Cpu,
  Database,
  Globe,
  Droplets,
  Calendar,
  Layers,
  ArrowRight,
  BookOpen
} from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 sm:p-6 shadow-xs">
        <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <Info className="w-4 h-4" />
          <span>System Architecture & Methodology</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
          About Groundwater AI Platform
        </h1>
        <p className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm mt-1 max-w-3xl leading-relaxed">
          An open data interface for exploring India's national groundwater assessment datasets through natural language queries. The system maps user requests to deterministic database queries, ensuring numerical reliability and transparent source citation.
        </p>
      </div>

      {/* Core Architectural Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-2.5">
          <div className="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 flex items-center justify-center text-blue-600 dark:text-blue-400">
            <Database className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-slate-900 dark:text-white text-sm">Grounded Database Dispatch</h3>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            All numerical responses originate from verified SQLite database records. The NLP engine parses intents and parameters without calculating numbers independently.
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-2.5">
          <div className="w-9 h-9 rounded-lg bg-teal-50 dark:bg-teal-900/30 border border-teal-200 dark:border-teal-800 flex items-center justify-center text-teal-600 dark:text-teal-400">
            <Cpu className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-slate-900 dark:text-white text-sm">Multi-Model NLP Engine</h3>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Combines deterministic regex pattern matching for instant answers, Scikit-Learn TF-IDF classification (89.75% benchmark accuracy), and Gemini Flash fallback.
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-2.5">
          <div className="w-9 h-9 rounded-lg bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 flex items-center justify-center text-slate-700 dark:text-slate-300">
            <Calendar className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-slate-900 dark:text-white text-sm">Multi-Year Temporal Scope</h3>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Displays only individually verified assessment records. Assessment year, publication year, data year, and source document are tracked separately; unknown dates are left unspecified.
          </p>
        </div>
      </div>

      {/* Hydrogeological Primer */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-3.5">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2">
          <Droplets className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span>IN-GRES & CGWB Domain Reference</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
          <div className="bg-slate-50 dark:bg-slate-900 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 space-y-1.5">
            <h4 className="font-semibold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">Primary Authority</h4>
            <p>
              <strong>Central Ground Water Board (CGWB)</strong> under the Ministry of Jal Shakti, Government of India,
              is the national apex agency providing scientific inputs for exploration, monitoring, and sustainable management of groundwater resources.
            </p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 space-y-1.5">
            <h4 className="font-semibold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">Measurement Standards</h4>
            <p>
              All volumetric measurements are quantified in <strong>Hectare Meters (Ham)</strong>, where{' '}
              <span className="font-mono text-slate-800 dark:text-slate-200 font-medium">1 Ham = 10,000 m³ = 10 million liters</span>. Stage of extraction expresses total annual extraction as a percentage of net annual extractable resources.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
