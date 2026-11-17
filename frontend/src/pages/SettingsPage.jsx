import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Sun,
  Moon,
  Cpu,
  Database,
  Trash2,
  CheckCircle2,
  RefreshCw,
  Globe,
  Shield
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { getHealth } from '../services/api';

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const [defaultMode, setDefaultMode] = useState('hybrid');
  const [cleared, setCleared] = useState(false);
  const [healthStatus, setHealthStatus] = useState(null);
  const [checking, setChecking] = useState(false);

  const handleClearCache = () => {
    localStorage.removeItem('gw_ai_session');
    setCleared(true);
    setTimeout(() => setCleared(false), 2500);
  };

  const handleTestConnection = () => {
    setChecking(true);
    getHealth()
      .then((res) => setHealthStatus(res.data))
      .catch(() => setHealthStatus({ status: 'offline' }))
      .finally(() => setChecking(false));
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 sm:p-6 shadow-xs">
        <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <SettingsIcon className="w-4 h-4" />
          <span>Configuration & Preferences</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
          Platform Settings
        </h1>
        <p className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
          Manage interface display theme, NLP model execution mode, and database service connectivity.
        </p>
      </div>

      <div className="space-y-4">
        {/* Appearance */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-3">
          <h2 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">Display Theme</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white">Interface Mode</div>
              <div className="text-xs text-slate-500">Switch between Light (default research portal) and Dark theme</div>
            </div>
            <button
              onClick={toggleTheme}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-xs font-medium text-slate-800 dark:text-slate-200 hover:bg-slate-100 transition-colors"
            >
              {theme === 'dark' ? (
                <>
                  <Moon className="w-4 h-4 text-blue-400" />
                  <span>Dark Mode</span>
                </>
              ) : (
                <>
                  <Sun className="w-4 h-4 text-amber-500" />
                  <span>Light Mode</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* NLP Model Engine */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-3">
          <h2 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">NLP Query Engine</h2>
          <div className="space-y-2.5">
            {[
              { id: 'hybrid', label: 'Hybrid Ensemble (Recommended)', desc: 'Combines deterministic rule safety with Scikit-Learn ML and Gemini Flash' },
              { id: 'ml', label: 'Scikit-Learn ML Baseline (TF-IDF + LogReg)', desc: '100% offline statistical classification (89.75% benchmark accuracy)' },
              { id: 'rule_based', label: 'Rule-Based Engine', desc: 'Deterministic regex pattern matching with sub-millisecond execution' },
            ].map((engine) => (
              <label
                key={engine.id}
                className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  defaultMode === engine.id
                    ? 'bg-blue-50/60 dark:bg-blue-950/30 border-blue-400 dark:border-blue-700'
                    : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="defaultMode"
                  value={engine.id}
                  checked={defaultMode === engine.id}
                  onChange={(e) => setDefaultMode(e.target.value)}
                  className="mt-0.5 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-white">{engine.label}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{engine.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Backend & Connectivity */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-3">
          <h2 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">Backend API Connectivity</h2>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <div className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white">Local REST API Service</div>
              <div className="text-xs text-slate-500 font-mono">http://127.0.0.1:8000/api</div>
            </div>
            <button
              onClick={handleTestConnection}
              disabled={checking}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-xs font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
              <span>Ping Backend Health</span>
            </button>
          </div>
          {healthStatus && (
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs space-y-1 font-mono">
              <div className="text-blue-700 dark:text-blue-300 font-semibold">Status: {healthStatus.status}</div>
              {healthStatus.total_records !== undefined && (
                <div className="text-slate-600 dark:text-slate-400">Verified DB Records: {healthStatus.total_records}</div>
              )}
            </div>
          )}
        </div>

        {/* Cache & Reset */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-3">
          <h2 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">Session Cache</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white">Clear Local Session History</div>
              <div className="text-xs text-slate-500">Purge cached chat threads and context cookies from browser storage</div>
            </div>
            <button
              onClick={handleClearCache}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 hover:bg-rose-50 hover:border-rose-300 hover:text-rose-600 text-xs font-medium text-slate-700 dark:text-slate-300 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{cleared ? 'Cleared!' : 'Clear Cache'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
