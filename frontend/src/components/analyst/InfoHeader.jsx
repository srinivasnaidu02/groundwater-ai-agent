import React from 'react';

export default function InfoHeader() {
  return (
    <div className="border-l-4 border-l-teal-500 bg-[#0f1f33] rounded-lg p-5 sm:p-6 border border-slate-800/80 shadow-md">
      <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
        INGRES-Agent — Groundwater Virtual Assistant
      </h1>
      <p className="text-sm text-slate-300 mt-2 leading-relaxed">
        Ask natural-language questions about India's official groundwater resource assessments:
        annual recharge, extractable resources, total extraction, extraction stage (%), and assessment unit categorization.
      </p>
      <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs text-slate-400 leading-normal">
        <span className="font-semibold text-slate-300">Scope:</span> Groundwater resource assessments (ham / bcm) and unit categorization.
        Measured depth-to-water-level (mbgl) and water-quality metrics are not covered.
      </div>
    </div>
  );
}
