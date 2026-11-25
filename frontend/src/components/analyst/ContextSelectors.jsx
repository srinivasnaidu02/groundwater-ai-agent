import React from 'react';
import { HelpCircle, RefreshCw } from 'lucide-react';

export default function ContextSelectors({
  years,
  states,
  districts,
  selectedYear,
  selectedState,
  selectedDistrict,
  onYearChange,
  onStateChange,
  onDistrictChange,
  loadingYears,
  loadingStates,
  loadingDistricts,
  errorStates,
  onRetryStates,
  validationErrors = {},
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400">
        Assessment Year <span className="text-teal-400 font-semibold">*</span> is required. State is required for single-location queries (or specify in question / comparison).
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Assessment Year Select */}
        <div>
          <label
            htmlFor="select-year"
            className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-1.5"
          >
            <span>Assessment Year <span className="text-teal-400">*</span></span>
            <span
              title="Official Central Ground Water Board (CGWB) annual assessment cycle (2020-2026)"
              className="cursor-help text-slate-500 hover:text-slate-300 transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
            </span>
          </label>
          <div className="relative">
            <select
              id="select-year"
              value={selectedYear || ''}
              onChange={(e) => onYearChange(e.target.value)}
              disabled={loadingYears}
              aria-invalid={!!validationErrors.year}
              className={`w-full bg-[#0b1a2d] border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all ${
                validationErrors.year ? 'border-red-500' : 'border-slate-700/80 hover:border-slate-600'
              }`}
            >
              {years.map((y) => (
                <option key={y} value={y} className="bg-[#0b1a2d] text-slate-200">
                  {y} {y === '2026' ? '(Benchmark Projection)' : ''}
                </option>
              ))}
            </select>
            {loadingYears && (
              <RefreshCw className="w-3.5 h-3.5 text-teal-400 animate-spin absolute right-8 top-3 pointer-events-none" />
            )}
          </div>
          {validationErrors.year && (
            <p className="text-[11px] text-red-400 mt-1">{validationErrors.year}</p>
          )}
        </div>

        {/* State / UT Select */}
        <div>
          <label
            htmlFor="select-state"
            className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-1.5"
          >
            <span>State / Union Territory</span>
            <span className="text-[11px] text-slate-400 font-normal">(or comparison in question)</span>
            <span
              title="Select one of 31 Indian States or Union Territories, or leave as Multi-State for comparison questions"
              className="cursor-help text-slate-500 hover:text-slate-300 transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
            </span>
          </label>
          <div className="relative">
            <select
              id="select-state"
              value={selectedState || ''}
              onChange={(e) => onStateChange(e.target.value)}
              disabled={loadingStates}
              aria-invalid={!!validationErrors.state}
              className={`w-full bg-[#0b1a2d] border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all ${
                validationErrors.state ? 'border-red-500' : 'border-slate-700/80 hover:border-slate-600'
              }`}
            >
              <option value="" className="bg-[#0b1a2d] text-slate-300">
                {loadingStates ? 'Loading States...' : 'Select State / UT (or Multi-State Comparison)'}
              </option>
              {states.map((st) => (
                <option key={st} value={st} className="bg-[#0b1a2d] text-slate-200">
                  {st}
                </option>
              ))}
            </select>
            {loadingStates && (
              <RefreshCw className="w-3.5 h-3.5 text-teal-400 animate-spin absolute right-8 top-3 pointer-events-none" />
            )}
          </div>
          {errorStates && (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[11px] text-red-400">Could not load states.</span>
              <button
                type="button"
                onClick={onRetryStates}
                className="text-[11px] text-teal-400 underline hover:text-teal-300"
              >
                Retry
              </button>
            </div>
          )}
          {validationErrors.state && (
            <p className="text-[11px] text-red-400 mt-1">{validationErrors.state}</p>
          )}
        </div>

        {/* District (Optional) Select */}
        <div>
          <label
            htmlFor="select-district"
            className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-1.5"
          >
            <span>District (Optional)</span>
            <span
              title="Specific administrative district, or leave as State-level (no district)"
              className="cursor-help text-slate-500 hover:text-slate-300 transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
            </span>
          </label>
          <div className="relative">
            <select
              id="select-district"
              value={selectedDistrict || ''}
              onChange={(e) => onDistrictChange(e.target.value)}
              disabled={!selectedState || loadingDistricts}
              className="w-full bg-[#0b1a2d] border border-slate-700/80 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 disabled:opacity-50 disabled:cursor-not-allowed hover:border-slate-600 transition-all"
            >
              <option value="" className="bg-[#0b1a2d] text-slate-300">
                {selectedState ? 'State-level (no district)' : 'No district (Comparison / All-State)'}
              </option>
              {districts.map((d) => (
                <option key={d} value={d} className="bg-[#0b1a2d] text-slate-200">
                  {d}
                </option>
              ))}
            </select>
            {loadingDistricts && (
              <RefreshCw className="w-3.5 h-3.5 text-teal-400 animate-spin absolute right-8 top-3 pointer-events-none" />
            )}
          </div>
          {!selectedState ? (
            <p className="text-[11px] text-slate-500 mt-1">Select a State to view districts (or leave empty for comparisons)</p>
          ) : (
            <p className="text-[11px] text-slate-400 mt-1">
              {loadingDistricts
                ? 'Fetching districts...'
                : `${districts.length} districts available`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
