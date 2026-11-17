import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  HelpCircle,
  Layers,
  ArrowUpRight,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  ExternalLink,
  X,
  Droplets,
  Activity,
  Sliders,
  Maximize2
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea
} from 'recharts';
import { queryNL } from '../services/api';
import {
  YEAR_TO_COVERAGE_MAP,
  SUPPORTED_ASSESSMENT_YEARS,
} from '../constants/coverageData';
import { useGroundwaterAnalytics } from '../hooks/useGroundwaterAnalytics';

export default function ChatPage() {
  // Query Form State
  const [assessmentYear, setAssessmentYear] = useState('2025');
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [question, setQuestion] = useState('What is the groundwater extraction in Patna in 2025?');

  // Query Execution State
  const [loading, setLoading] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Map Controls State
  const [mapZoom, setMapZoom] = useState(50);
  const [showOverlays, setShowOverlays] = useState(true);

  // Dynamic coverage derivation for current selection
  const yearCoverage = YEAR_TO_COVERAGE_MAP[assessmentYear] || {};
  const availableStates = useMemo(() => Object.keys(yearCoverage).sort(), [yearCoverage]);
  const availableDistricts = useMemo(() => {
    return selectedState && yearCoverage[selectedState]
      ? [...yearCoverage[selectedState]].sort()
      : [];
  }, [yearCoverage, selectedState]);

  // Central Dynamic Analytics Hook
  const analytics = useGroundwaterAnalytics({
    year: assessmentYear,
    state: selectedState,
    district: selectedDistrict,
    lastQueryResult: queryResult,
  });

  // When Assessment Year changes: cascade and filter states and districts
  const handleYearChange = (newYear) => {
    setAssessmentYear(newYear);
    const newCoverage = YEAR_TO_COVERAGE_MAP[newYear] || {};
    const newStates = Object.keys(newCoverage);

    let nextState = selectedState;
    let nextDistrict = selectedDistrict;

    if (!newStates.includes(selectedState)) {
      nextState = '';
      nextDistrict = '';
      setSelectedState('');
      setSelectedDistrict('');
    } else {
      const newDistricts = newCoverage[selectedState] || [];
      if (selectedDistrict && !newDistricts.includes(selectedDistrict)) {
        nextDistrict = '';
        setSelectedDistrict('');
      }
    }

    if (nextDistrict && nextState) {
      const loc = nextDistrict.toLowerCase().endsWith(nextState.toLowerCase())
        ? nextDistrict
        : `${nextDistrict}, ${nextState}`;
      setQuestion(`What is the groundwater extraction in ${loc} in ${newYear}?`);
    } else if (nextState) {
      setQuestion(`What is the total annual groundwater recharge in ${nextState} in ${newYear}?`);
    } else {
      setQuestion(`What is the groundwater extraction in Patna in ${newYear}?`);
    }
  };

  // When State changes: reset district to State-level
  const handleStateChange = (st) => {
    setSelectedState(st);
    setSelectedDistrict('');
    if (st) {
      setQuestion(`What is the total annual groundwater recharge in ${st} in ${assessmentYear}?`);
    } else {
      setQuestion(`What is the groundwater extraction in Patna in ${assessmentYear}?`);
    }
  };

  // When District changes: update question
  const handleDistrictChange = (dist) => {
    setSelectedDistrict(dist);
    if (dist && selectedState) {
      const loc = dist.toLowerCase().endsWith(selectedState.toLowerCase())
        ? dist
        : `${dist}, ${selectedState}`;
      setQuestion(`What is the groundwater extraction in ${loc} in ${assessmentYear}?`);
    } else if (selectedState) {
      setQuestion(`What is the total annual groundwater recharge in ${selectedState} in ${assessmentYear}?`);
    } else {
      setQuestion(`What is the groundwater extraction in Patna in ${assessmentYear}?`);
    }
  };

  // Helper to synchronize UI state from query text or AI response entities
  const syncEntitiesToFilters = (entities, rawQuery = '') => {
    let yr = entities?.assessment_year ? String(entities.assessment_year) : null;
    let st = entities?.state ? String(entities.state) : null;
    let dst = entities?.district ? String(entities.district) : null;

    // Fallback: regex scan in query string
    if (!yr && rawQuery) {
      const yearMatch = rawQuery.match(/\b(2020|2022|2023|2024|2025|2026)\b/);
      if (yearMatch) yr = yearMatch[1];
    }
    if (!st && rawQuery) {
      for (const knownState of Object.keys(YEAR_TO_COVERAGE_MAP['2022'] || {})) {
        if (new RegExp(`\\b${knownState}\\b`, 'i').test(rawQuery)) {
          st = knownState;
          break;
        }
      }
    }
    if (st && !dst && rawQuery) {
      const distList = YEAR_TO_COVERAGE_MAP['2022']?.[st] || [];
      for (const knownDist of distList) {
        if (new RegExp(`\\b${knownDist}\\b`, 'i').test(rawQuery)) {
          dst = knownDist;
          break;
        }
      }
    }

    const targetYear = yr && SUPPORTED_ASSESSMENT_YEARS.includes(yr) ? yr : assessmentYear;
    if (targetYear !== assessmentYear) {
      setAssessmentYear(targetYear);
    }

    const coverageForYear = YEAR_TO_COVERAGE_MAP[targetYear] || {};
    const validStates = Object.keys(coverageForYear);

    if (st) {
      const matchedState = validStates.find((s) => s.toLowerCase() === st.toLowerCase());
      if (matchedState) {
        setSelectedState(matchedState);
        if (dst) {
          const validDistricts = coverageForYear[matchedState] || [];
          const matchedDistrict = validDistricts.find((d) => d.toLowerCase() === dst.toLowerCase());
          if (matchedDistrict) {
            setSelectedDistrict(matchedDistrict);
          } else {
            setSelectedDistrict('');
          }
        }
      }
    }
  };

  // Execute Query
  const handleQuery = async (e) => {
    if (e) e.preventDefault();
    if (!question.trim()) return;

    // Immediate optimistic sync from question text
    syncEntitiesToFilters(null, question);

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await queryNL(question);
      setQueryResult(res.data);

      // Deep two-way sync from parsed AI entities
      if (res.data?.entities) {
        syncEntitiesToFilters(res.data.entities, question);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error executing query');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-3.5rem)] bg-[#07131e] text-slate-100 overflow-hidden px-4 sm:px-6 lg:px-8 py-6 flex flex-col justify-between select-none">
      {/* Background Glowing Bathymetric / Topographic Contours */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-30">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" viewBox="0 0 1440 900">
          <defs>
            <radialGradient id="oceanGlow" cx="50%" cy="20%" r="60%">
              <stop offset="0%" stopColor="#0284c7" stopOpacity="0.4" />
              <stop offset="60%" stopColor="#082f49" stopOpacity="0.1" />
              <stop offset="100%" stopColor="#07131e" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="waveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.35" />
              <stop offset="50%" stopColor="#0284c7" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.25" />
            </linearGradient>
          </defs>
          <rect width="100%" height="100%" fill="url(#oceanGlow)" />
          {/* Topographic Contour Lines */}
          <path d="M-100 220 Q 300 80, 720 200 T 1540 180" fill="none" stroke="url(#waveGrad)" strokeWidth="1.2" />
          <path d="M-100 270 Q 350 140, 750 240 T 1540 230" fill="none" stroke="url(#waveGrad)" strokeWidth="1" />
          <path d="M-100 330 Q 280 200, 700 310 T 1540 290" fill="none" stroke="url(#waveGrad)" strokeWidth="0.8" />
          <path d="M-100 400 Q 400 280, 800 370 T 1540 360" fill="none" stroke="url(#waveGrad)" strokeWidth="1" />
          <path d="M-100 480 Q 300 380, 740 460 T 1540 440" fill="none" stroke="url(#waveGrad)" strokeWidth="0.8" />
          <path d="M-100 560 Q 420 450, 820 540 T 1540 520" fill="none" stroke="url(#waveGrad)" strokeWidth="1" />
        </svg>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto w-full space-y-6">
        {/* Top Centered Header */}
        <div className="text-center space-y-2 pt-2 max-w-4xl mx-auto">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white drop-shadow-md">
            AI-Powered Groundwater Intelligence Agent
          </h1>
          <p className="text-xs sm:text-sm lg:text-base font-medium text-cyan-300/90 tracking-wide">
            Natural Language Query System for Groundwater Resource Analysis in India
          </p>
        </div>

        {/* Query Input Card */}
        <div className="bg-[#0b1d2e]/80 backdrop-blur-xl border border-cyan-500/25 rounded-2xl p-4 sm:p-5 shadow-2xl shadow-cyan-950/50 space-y-4">
          <form onSubmit={handleQuery} className="space-y-3.5">
            {/* Top Selector Row: 3 Dropdowns */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              {/* Assessment Year */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                  <span>Assessment Year <span className="text-cyan-400">*</span></span>
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400 hover:text-cyan-300 cursor-pointer" title="Select CGWB assessment reporting cycle" />
                </div>
                <select
                  value={assessmentYear}
                  onChange={(e) => handleYearChange(e.target.value)}
                  className="w-full bg-[#081524] border border-cyan-500/30 rounded-lg px-3 py-2 text-xs text-white focus:outline-hidden focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-colors"
                >
                  {SUPPORTED_ASSESSMENT_YEARS.map((yr) => (
                    <option key={yr} value={yr} className="bg-[#081524] text-white">
                      {yr}
                    </option>
                  ))}
                </select>
              </div>

              {/* State / UT */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                  <span>State / Union Territory <span className="text-cyan-400">*</span></span>
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400 hover:text-cyan-300 cursor-pointer" title="Select Indian State or Union Territory" />
                </div>
                <select
                  value={selectedState}
                  onChange={(e) => handleStateChange(e.target.value)}
                  className="w-full bg-[#081524] border border-cyan-500/30 rounded-lg px-3 py-2 text-xs text-white focus:outline-hidden focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-colors"
                >
                  <option value="" className="bg-[#081524] text-slate-400">Select State / UT</option>
                  {availableStates.map((st) => (
                    <option key={st} value={st} className="bg-[#081524] text-white">
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              {/* District */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                  <span>District (Optional)</span>
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400 hover:text-cyan-300 cursor-pointer" title="Leave blank for state-wide aggregate query" />
                </div>
                <select
                  value={selectedDistrict}
                  onChange={(e) => handleDistrictChange(e.target.value)}
                  disabled={!selectedState}
                  className="w-full bg-[#081524] border border-cyan-500/30 disabled:border-slate-800 disabled:opacity-50 rounded-lg px-3 py-2 text-xs text-white focus:outline-hidden focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-colors"
                >
                  <option value="" className="bg-[#081524] text-slate-400">State-level (no district)</option>
                  {availableDistricts.map((dst) => (
                    <option key={dst} value={dst} className="bg-[#081524] text-white">
                      {dst}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Bottom Question Input & Query Button */}
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">
                Your Question <span className="text-cyan-400">*</span>
              </label>
              <div className="relative flex items-center">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder='Ask a groundwater question (e.g. "What is the groundwater extraction in Patna in 2025?").'
                  className="w-full bg-[#081524] border border-cyan-500/35 rounded-xl pl-4 pr-32 py-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-hidden focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 transition-all shadow-inner"
                />
                <button
                  type="submit"
                  disabled={loading || !question.trim()}
                  className="absolute right-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 disabled:opacity-50 text-white font-semibold text-xs rounded-lg flex items-center space-x-1.5 shadow-md shadow-cyan-600/30 transition-all"
                >
                  <span>{loading ? 'Querying...' : 'Query'}</span>
                  <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </form>

          {/* Error Notice */}
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Expandable Result Card if executed */}
          {queryResult && (
            <div className="mt-4 pt-4 border-t border-cyan-500/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>Verified Query Result</span>
                </span>
                <button
                  onClick={() => setQueryResult(null)}
                  className="text-slate-400 hover:text-white p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Natural Language Answer */}
              <div className="p-3.5 rounded-xl bg-[#07131e]/90 border border-cyan-500/20 text-slate-200 text-xs leading-relaxed whitespace-pre-line">
                {queryResult.answer}
              </div>
            </div>
          )}
        </div>

        {/* Bottom Section: 3 High-Tech Dashboard Cards (Fully Dynamic) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* 1. Map Panel (Dynamic region & hotspots) */}
          <div className="bg-[#0a1e33]/70 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-4 flex flex-col justify-between shadow-xl shadow-cyan-950/30 min-h-[350px]">
            {/* Header with Dynamic Region Scope Badge */}
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <div className="flex flex-col">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  LIVE GROUNDWATER & Water Level Map
                </span>
                <span className="text-[10px] text-cyan-400 font-medium tracking-wide">
                  Scope: {analytics.scopeLabel}
                </span>
              </div>
              <div className="flex items-center space-x-1.5">
                <button
                  onClick={() => setShowOverlays(!showOverlays)}
                  className={`text-[10px] px-2 py-0.5 rounded-md border flex items-center space-x-1 transition-colors ${
                    showOverlays
                      ? 'bg-cyan-950/60 text-cyan-300 border-cyan-700/60'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  <Layers className="w-3 h-3" />
                  <span>Interactive Overlays</span>
                </button>
              </div>
            </div>

            {/* Interactive Heatmap Canvas / SVG */}
            <div className="relative flex-1 my-3 rounded-xl overflow-hidden bg-[#06121e] border border-cyan-900/30 flex items-center justify-center">
              {/* Zoom Slider Control on left */}
              <div className="absolute left-2.5 top-1/2 -translate-y-1/2 z-20 flex flex-col items-center bg-[#0a1e33]/90 border border-slate-700/80 rounded-full py-2 px-1 space-y-2 shadow-lg">
                <button onClick={() => setMapZoom(Math.min(100, mapZoom + 10))} className="text-slate-300 hover:text-white text-xs font-bold">+</button>
                <div className="w-1 h-12 bg-slate-700 rounded-full relative">
                  <div
                    className="w-2.5 h-2.5 -left-[3px] bg-cyan-400 rounded-full absolute shadow-xs shadow-cyan-400"
                    style={{ top: `${100 - mapZoom}%` }}
                  />
                </div>
                <button onClick={() => setMapZoom(Math.max(10, mapZoom - 10))} className="text-slate-300 hover:text-white text-xs font-bold">-</button>
              </div>

              {/* Dynamic Topographic Heatmap Rendering */}
              <svg className="w-full h-48 sm:h-56" viewBox="0 0 400 240" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  {/* Heatmap Gradients */}
                  <radialGradient id="heatCritical" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.95" />
                    <stop offset="40%" stopColor="#f59e0b" stopOpacity="0.75" />
                    <stop offset="70%" stopColor="#06b6d4" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#082f49" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="heatRecharge" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.85" />
                    <stop offset="60%" stopColor="#0284c7" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#082f49" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="heatSelected" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#38bdf8" stopOpacity="1" />
                    <stop offset="60%" stopColor="#0284c7" stopOpacity="0.6" />
                    <stop offset="100%" stopColor="#082f49" stopOpacity="0" />
                  </radialGradient>
                </defs>

                {/* State/Region Boundary Shape */}
                <path
                  d="M 60,140 Q 100,100 160,110 T 260,95 Q 320,110 350,150 T 320,190 Q 240,210 180,200 T 70,180 Z"
                  fill="#0b2438"
                  stroke="#38bdf8"
                  strokeWidth="1.5"
                  strokeDasharray="2 2"
                />

                {/* Dynamic District Heatmap Blobs */}
                {showOverlays && analytics.districts.slice(0, 14).map((d) => (
                  <ellipse
                    key={d.id}
                    cx={d.xOffset}
                    cy={d.yOffset}
                    rx={d.isOverExploited ? 40 : d.isCritical ? 30 : 25}
                    ry={d.isOverExploited ? 28 : d.isCritical ? 22 : 18}
                    fill={d.isOverExploited ? "url(#heatCritical)" : "url(#heatRecharge)"}
                    filter="blur(5px)"
                    opacity={0.8}
                  />
                ))}

                {/* Center State Name Label */}
                <text x="200" y="152" fill="#ffffff" fontSize="13" fontWeight="bold" textAnchor="middle" letterSpacing="0.8" className="drop-shadow-md">
                  {analytics.activeState}
                </text>

                {/* Dynamic Callout 1: Highest Extraction (Red) */}
                <g className="cursor-pointer">
                  <circle cx="120" cy="142" r="5" fill="#ef4444" />
                  <circle cx="120" cy="142" r="9" stroke="#ef4444" strokeWidth="1" strokeOpacity="0.6" className="animate-ping" />
                  <rect x="52" y="114" width="136" height="19" rx="4" fill="#081524" fillOpacity="0.9" stroke="#ef4444" strokeWidth="0.8" />
                  <circle cx="60" cy="123" r="3" fill="#ef4444" />
                  <text x="68" y="126" fill="#fecaca" fontSize="8" fontWeight="600">
                    Over-exploited: {analytics.highestDistrict.name} ({analytics.highestDistrict.stage}%)
                  </text>
                </g>

                {/* Dynamic Callout 2: Safe / High Recharge (Blue) */}
                <g className="cursor-pointer">
                  <circle cx="280" cy="128" r="4.5" fill="#06b6d4" />
                  <circle cx="280" cy="128" r="8" stroke="#06b6d4" strokeWidth="1" strokeOpacity="0.6" />
                  <rect x="215" y="100" width="145" height="19" rx="4" fill="#081524" fillOpacity="0.9" stroke="#06b6d4" strokeWidth="0.8" />
                  <circle cx="223" cy="109" r="3" fill="#06b6d4" />
                  <text x="231" y="112" fill="#cffafe" fontSize="8" fontWeight="600">
                    Safe Zone: {analytics.lowestDistrict.name} ({analytics.lowestDistrict.stage}%)
                  </text>
                </g>

                {/* Pulse highlight if a specific district is selected */}
                {selectedDistrict && (
                  <g className="cursor-pointer">
                    <circle cx="200" cy="125" r="7" fill="#38bdf8" />
                    <circle cx="200" cy="125" r="14" stroke="#38bdf8" strokeWidth="1.5" strokeOpacity="0.8" className="animate-ping" />
                    <rect x="145" y="80" width="110" height="20" rx="4" fill="#0369a1" fillOpacity="0.95" stroke="#38bdf8" strokeWidth="1" />
                    <text x="200" y="93" fill="#ffffff" fontSize="8.5" fontWeight="bold" textAnchor="middle">
                      Selected: {selectedDistrict}
                    </text>
                  </g>
                )}
              </svg>

              {/* Zoom Scale Pill */}
              <div className="absolute right-2.5 bottom-2.5 bg-[#0a1e33]/90 text-[10px] text-slate-300 font-mono px-2 py-0.5 rounded border border-slate-700">
                Zoom Scale
              </div>
            </div>

            {/* Bottom Legend */}
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-300">
              <span className="font-semibold text-slate-400">Map Legend</span>
              <div className="flex items-center space-x-3">
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                  <span>Over-exploited</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                  <span>Semi-Critical</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                  <span>Recharge/Safe</span>
                </span>
              </div>
            </div>
          </div>

          {/* 2. Historical Trend Chart Panel (Dynamic Multi-Year Line Chart) */}
          <div className="bg-[#0a1e33]/70 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-4 flex flex-col justify-between shadow-xl shadow-cyan-950/30 min-h-[350px]">
            {/* Header with 3 Distinct Computed KPIs */}
            <div className="space-y-2 pb-2 border-b border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Historical Extraction Trend Chart
                </span>
              </div>

              {/* 3 Real Computed KPI Pills */}
              <div className="grid grid-cols-3 gap-2">
                {/* 1. Avg. Stage of Extraction */}
                <div className="bg-[#071524] border border-amber-600/30 rounded-lg p-1.5 text-center">
                  <div className="text-[9px] text-slate-400 flex items-center justify-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                    <span>Avg. Extraction</span>
                  </div>
                  <div className="text-xs font-bold text-amber-400 font-mono mt-0.5">
                    {analytics.avgStageOfExtraction}%
                  </div>
                </div>

                {/* 2. Annual Recharge */}
                <div className="bg-[#071524] border border-cyan-600/30 rounded-lg p-1.5 text-center">
                  <div className="text-[9px] text-slate-400 flex items-center justify-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span>Annual Recharge</span>
                  </div>
                  <div className="text-xs font-bold text-cyan-400 font-mono mt-0.5">
                    {analytics.totalRechargeBcm} BCM
                  </div>
                </div>

                {/* 3. Annual Extraction (Fixed from duplicate Recharge) */}
                <div className="bg-[#071524] border border-emerald-600/30 rounded-lg p-1.5 text-center">
                  <div className="text-[9px] text-slate-400 flex items-center justify-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>Annual Extraction</span>
                  </div>
                  <div className="text-xs font-bold text-emerald-400 font-mono mt-0.5">
                    {analytics.totalExtractionBcm} BCM
                  </div>
                </div>
              </div>
            </div>

            {/* Dynamic Chart Subtitle */}
            <div className="pt-2 text-[11px] font-semibold text-slate-300 truncate">
              Groundwater Extraction vs. Recharge Trends in {analytics.activeDistrict ? `${analytics.activeDistrict}, ` : ''}{analytics.activeState} (2020–2026)
            </div>

            {/* Recharts Chart with Dynamic Dataset Data */}
            <div className="flex-1 w-full h-44 sm:h-48 pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.historicalTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#162e47" vertical={false} />
                  <XAxis dataKey="year" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#071524', borderColor: '#0284c7', borderRadius: '8px', fontSize: '11px' }}
                    labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                    formatter={(val, name) => [`${val}k Ham`, name]}
                  />
                  {/* Highlight current active assessment year */}
                  <ReferenceArea
                    x1={assessmentYear}
                    x2={assessmentYear}
                    stroke="#38bdf8"
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                    fill="#0284c7"
                    fillOpacity={0.12}
                  />

                  {/* Extraction Line (Orange / Red) */}
                  <Line
                    type="monotone"
                    dataKey="extraction"
                    name="Extraction Line"
                    stroke="#f97316"
                    strokeWidth={2.2}
                    dot={{ r: 3, fill: '#f97316' }}
                    activeDot={{ r: 5 }}
                  />
                  {/* Recharge Line (Cyan) */}
                  <Line
                    type="monotone"
                    dataKey="recharge"
                    name="Recharge"
                    stroke="#06b6d4"
                    strokeWidth={2.2}
                    dot={{ r: 3, fill: '#06b6d4' }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Legend & Active Year Indicator */}
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
              <div className="flex items-center space-x-3">
                <span className="flex items-center space-x-1 text-slate-300">
                  <span className="w-3 h-0.5 bg-amber-500 inline-block" />
                  <span>Extraction</span>
                </span>
                <span className="flex items-center space-x-1 text-slate-300">
                  <span className="w-3 h-0.5 bg-cyan-400 inline-block" />
                  <span>Recharge</span>
                </span>
              </div>
              <span className="text-[9px] font-mono text-cyan-300 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/40">
                Active Year: {assessmentYear}
              </span>
            </div>
          </div>

          {/* 3. Real-Time Insights & Key Metrics Panel (Fully Dynamic) */}
          <div className="bg-[#0a1e33]/70 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-4 flex flex-col justify-between shadow-xl shadow-cyan-950/30 min-h-[350px]">
            {/* Header */}
            <div className="pb-2 border-b border-slate-800/80">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Real-Time Insights & Key Metrics
              </span>
            </div>

            {/* Dynamic Gauge Circle: Recharge Efficiency */}
            <div className="flex items-center justify-center py-2">
              <div className="relative w-28 h-28 flex items-center justify-center">
                {/* Background Ring */}
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#102a43"
                    strokeWidth="8"
                  />
                  {/* Dynamic Progress Arc */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#06b6d4"
                    strokeWidth="8"
                    strokeDasharray="251.2"
                    strokeDashoffset={251.2 * (1 - Math.min(100, analytics.rechargeEfficiency) / 100)}
                    strokeLinecap="round"
                    className="transition-all duration-700 ease-out drop-shadow-[0_0_8px_rgba(6,182,212,0.6)]"
                  />
                </svg>
                {/* Dynamic Center Value */}
                <div className="absolute flex flex-col items-center justify-center text-center">
                  <span className="text-2xl font-black text-white font-mono tracking-tight">
                    {analytics.rechargeEfficiency}%
                  </span>
                  <span className="text-[9px] text-cyan-400 font-semibold leading-tight">
                    Recharge<br />Efficiency
                  </span>
                </div>
              </div>
            </div>

            {/* Dynamic 3 Status Notification Cards */}
            <div className="space-y-2">
              {/* Critical Sites Row */}
              <div className="bg-[#081726] border border-rose-900/40 rounded-xl p-2.5 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0 shadow-xs shadow-rose-500" />
                  <span className="font-semibold text-rose-300">CRITICAL SITES:</span>
                  <span className="text-slate-300 truncate max-w-[170px]">
                    {analytics.isDistrictScope
                      ? `${analytics.selectedDistrictRecord?.category || 'Safe'} (${analytics.avgStageOfExtraction}%)`
                      : `${analytics.criticalCount} of ${analytics.totalDistrictsCount} in ${analytics.activeState}`}
                  </span>
                </div>
              </div>

              {/* Safe Zones Row */}
              <div className="bg-[#081726] border border-cyan-900/40 rounded-xl p-2.5 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-teal-400 shrink-0 shadow-xs shadow-teal-400" />
                  <span className="font-semibold text-cyan-300">SAFE ZONES:</span>
                  <span className="text-slate-300 truncate max-w-[170px]">
                    {analytics.isDistrictScope
                      ? `Stage: ${analytics.avgStageOfExtraction}% (Safe ≤70%)`
                      : `${analytics.safeCount} Districts (e.g., ${analytics.topSafeDistrict})`}
                  </span>
                </div>
              </div>

              {/* Live Alert Feed Box (Derived from Query Answer or Dataset Insight) */}
              <div className="bg-[#06121d] border border-slate-800 rounded-xl p-2.5 space-y-1">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="font-semibold text-cyan-400 flex items-center space-x-1">
                    <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
                    <span>Insight Alert</span>
                  </span>
                  <span className="text-slate-400 text-[9px] font-mono">Live feed</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-snug line-clamp-2">
                  {analytics.insightAlert}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
