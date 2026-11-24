import React from 'react';
import { Send, RefreshCw, AlertCircle } from 'lucide-react';

export default function QuestionForm({
  query,
  onQueryChange,
  onSubmit,
  loading,
  validationError,
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="bg-[#0f1f33] rounded-lg p-5 border border-slate-800/80 shadow-md space-y-4">
      <div>
        <label
          htmlFor="question-input"
          className="block text-xs font-semibold text-slate-200 mb-2 uppercase tracking-wider"
        >
          Your Question <span className="text-teal-400">*</span>
        </label>
        <textarea
          id="question-input"
          rows={2}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          placeholder="e.g., What is the groundwater extraction stage? or Show groundwater summary"
          aria-invalid={!!validationError}
          className="w-full bg-[#0b1a2d] border border-slate-700/80 rounded-lg px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all resize-none font-sans"
        />
      </div>

      {validationError && (
        <div
          role="alert"
          className="flex items-center gap-2 p-2.5 rounded-md bg-red-950/40 border border-red-500/40 text-xs text-red-300"
        >
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      <div className="flex justify-start">
        <button
          type="button"
          onClick={onSubmit}
          disabled={loading}
          className="px-6 py-2.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-sm transition-all shadow-md shadow-teal-900/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
              <span>Analyzing CGWB Data...</span>
            </>
          ) : (
            <>
              <span>Submit</span>
              <Send className="w-4 h-4 text-slate-950" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
