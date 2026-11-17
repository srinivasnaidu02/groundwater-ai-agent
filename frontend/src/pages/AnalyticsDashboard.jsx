import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';
import {
  BarChart3,
  Calendar,
  Layers,
  MapPin,
  Search,
  CheckCircle,
  AlertTriangle,
  Droplets,
  Activity,
  ArrowUpRight,
  TrendingDown,
  TrendingUp,
  ShieldCheck,
  Building,
  Wheat,
  Factory
} from 'lucide-react';
import {
  getStateComparison,
  getCategoryDistribution,
  getDistrictData,
  getStates,
  getDistricts,
  getAssessmentYears,
  getDistrictMultiyear
} from '../services/api';

const CATEGORY_COLORS = {
  Safe: '#10b981',           // Emerald
  'Semi-Critical': '#f59e0b', // Amber
  Critical: '#ea580c',       // Orange
  'Over-Exploited': '#ef4444', // Red
  'Saline': '#8b5cf6',       // Purple
};

export default function AnalyticsDashboard() {
  const [year, setYear] = useState('2025');
  const [availableYears, setAvailableYears] = useState(['2020', '2021', '2022', '2023', '2024', '2025']);
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState('Bihar');
  const [districts, setDistricts] = useState([]);
  const [selectedDistrict, setSelectedDistrict] = useState('ALL');
  const [districtData, setDistrictData] = useState([]);
  const [districtMultiyear, setDistrictMultiyear] = useState(null);
  const [stateComparison, setStateComparison] = useState([]);
  const [categoryDist, setCategoryDist] = useState([]);
  const [provenance, setProvenance] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  // Load Initial Options (Years and States)
  useEffect(() => {
    getAssessmentYears()
      .then((res) => {
        const yrs = res.data?.assessment_years || [];
        if (yrs.length > 0) {
          setAvailableYears(yrs);
          if (yrs.includes('2025')) setYear('2025');
          else setYear(yrs[yrs.length - 1]);
        }
      })
      .catch((err) => console.error(err));

    getStates()
      .then((res) => {
        const list = res.data.states || [];
        setStates(list);
        if (list.includes('Bihar')) setSelectedState('Bihar');
        else if (list.length > 0) setSelectedState(list[0]);
      })
      .catch((err) => console.error(err));
  }, []);

  // When State Changes: fetch districts for dropdown
  useEffect(() => {
    if (!selectedState) return;
    getDistricts(selectedState)
      .then((res) => {
        const distList = res.data.districts || [];
        setDistricts(distList);
        setSelectedDistrict('ALL');
      })
      .catch((err) => console.error(err));
  }, [selectedState]);

  // Fetch State Comparison, Categories, and District Data for selected year and state
  useEffect(() => {
    setLoading(true);
    Promise.all([
      getStateComparison(year),
      getCategoryDistribution(year, selectedState),
      selectedState ? getDistrictData(selectedState, year) : Promise.resolve({ data: { districts: [] } }),
    ])
      .then(([stateRes, catRes, distRes]) => {
        setStateComparison(stateRes.data.states || []);
        setCategoryDist(catRes.data.distribution || []);
        setDistrictData(distRes.data.districts || []);
        setProvenance(stateRes.data.provenance?.[0] || null);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [year, selectedState]);

  // When individual district is selected: fetch its multi-year profile
  useEffect(() => {
    if (selectedDistrict && selectedDistrict !== 'ALL' && selectedState) {
      getDistrictMultiyear(selectedState, selectedDistrict)
        .then((res) => {
          setDistrictMultiyear(res.data);
        })
        .catch((err) => {
          console.error(err);
          setDistrictMultiyear(null);
        });
    } else {
      setDistrictMultiyear(null);
    }
  }, [selectedDistrict, selectedState]);

  const sumAvailable = (key) => {
    const values = stateComparison
      .map((item) => item[key])
      .filter((value) => typeof value === 'number');
    return values.length ? values.reduce((total, value) => total + value, 0) : null;
  };
  const totalRecharge = sumAvailable('total_recharge_ham');
  const totalExtraction = sumAvailable('total_extraction_ham');
  const totalExtractable = sumAvailable('total_extractable_ham');
  const overExploitedCount = categoryDist.find((c) => c.category === 'Over-Exploited')?.count || 0;

  // Filter district table rows by search and selectedDistrict
  const filteredDistricts = districtData.filter((d) => {
    const matchesSearch = d.district.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDistrict = selectedDistrict === 'ALL' || d.district.toLowerCase() === selectedDistrict.toLowerCase();
    return matchesSearch && matchesDistrict;
  });

  const activeDistrictRecord = districtData.find(
    (d) => selectedDistrict !== 'ALL' && d.district.toLowerCase() === selectedDistrict.toLowerCase()
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header & Interactive Control Bar */}
      <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">
              <Activity className="w-4 h-4" />
              <span>National Groundwater Observatory</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Dynamic Groundwater Resource Analytics
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Multi-year assessment coverage across 38 States/UTs and 621 Districts (Cycles 2020–2026).
            </p>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <span className="px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-medium flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>621 Districts Assessed</span>
            </span>
          </div>
        </div>

        {/* Triple Selector: State, District, and Year */}
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs">
          {/* Year Selection */}
          <div className="space-y-1">
            <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <Calendar className="w-3.5 h-3.5 text-blue-600" />
              <span>Assessment Cycle:</span>
            </label>
            <select
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 font-semibold text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>Assessment Cycle {y}</option>
              ))}
            </select>
          </div>

          {/* State Selection */}
          <div className="space-y-1">
            <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" />
              <span>Select State / UT:</span>
            </label>
            <select
              value={selectedState}
              onChange={(e) => {
                setSelectedState(e.target.value);
                setSelectedDistrict('ALL');
              }}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 font-semibold text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
            >
              {states.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* District Selection */}
          <div className="space-y-1">
            <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <Layers className="w-3.5 h-3.5 text-purple-600" />
              <span>Select District:</span>
            </label>
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 font-semibold text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
            >
              <option value="ALL">All Districts ({districts.length})</option>
              {districts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Quick Filter Search */}
          <div className="space-y-1 sm:col-span-3 lg:col-span-1">
            <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <Search className="w-3.5 h-3.5 text-slate-500" />
              <span>Filter Table:</span>
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Search district name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg pl-3 pr-8 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ×
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Selected District Deep-Dive Spotlight Card */}
      {selectedDistrict !== 'ALL' && activeDistrictRecord && (
        <div className="bg-gradient-to-br from-blue-50/80 via-white to-indigo-50/50 dark:from-slate-800/90 dark:via-[#111c2e] dark:to-indigo-950/20 border-2 border-blue-200 dark:border-blue-800/60 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-blue-100 dark:border-slate-700">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold text-slate-900 dark:text-white">
                  {selectedDistrict}, {selectedState}
                </span>
                <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  activeDistrictRecord.assessment_category === 'Safe'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : activeDistrictRecord.assessment_category === 'Semi-Critical'
                    ? 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300'
                    : activeDistrictRecord.assessment_category === 'Critical'
                    ? 'bg-orange-50 text-orange-700 border-orange-300 dark:bg-orange-950/40 dark:text-orange-300'
                    : 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300'
                }`}>
                  {activeDistrictRecord.assessment_category}
                </span>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                  activeDistrictRecord.is_verified
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300'
                }`}>
                  {activeDistrictRecord.is_verified ? 'VERIFIED' : 'OFFICIAL COMPILATION'}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Detailed Assessment Breakdown for Cycle {year}
              </p>
            </div>
            <button
              onClick={() => setSelectedDistrict('ALL')}
              className="text-xs text-blue-600 dark:text-blue-400 font-semibold hover:underline"
            >
              ← Back to All Districts
            </button>
          </div>

          {/* 4 Metric Cards for this District */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-white dark:bg-slate-800/80 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Total Extraction</span>
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400 mt-1">
                {Number(activeDistrictRecord.total_annual_extraction_ham || 0).toLocaleString()} <span className="text-xs font-normal text-slate-500">Ham</span>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800/80 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Annual Recharge</span>
              <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                {Number(activeDistrictRecord.total_annual_recharge_ham || 0).toLocaleString()} <span className="text-xs font-normal text-slate-500">Ham</span>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800/80 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Extractable Resource</span>
              <div className="text-xl font-bold text-teal-600 dark:text-teal-400 mt-1">
                {Number(activeDistrictRecord.annual_extractable_groundwater_ham || 0).toLocaleString()} <span className="text-xs font-normal text-slate-500">Ham</span>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800/80 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Stage of Extraction</span>
              <div className="text-xl font-bold text-slate-900 dark:text-white mt-1">
                {activeDistrictRecord.stage_of_extraction_pct ? `${activeDistrictRecord.stage_of_extraction_pct}%` : 'N/A'}
              </div>
            </div>
          </div>

          {/* Sector Breakdown & Multi-Year Trend for this District */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
            {/* Sector Use Allocation */}
            <div className="bg-white dark:bg-slate-800/80 p-4 rounded-lg border border-slate-200 dark:border-slate-700 space-y-3">
              <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider block">
                Extraction Sectoral Allocation (Cycle {year})
              </span>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2.5 rounded bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-800/40">
                  <Wheat className="w-4 h-4 text-emerald-600 mx-auto mb-1" />
                  <span className="text-[10px] text-slate-500 uppercase block">Irrigation</span>
                  <span className="font-bold text-slate-900 dark:text-white">
                    {Number(activeDistrictRecord.irrigation_extraction_ham || 0).toLocaleString()} Ham
                  </span>
                </div>
                <div className="p-2.5 rounded bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-800/40">
                  <Building className="w-4 h-4 text-blue-600 mx-auto mb-1" />
                  <span className="text-[10px] text-slate-500 uppercase block">Domestic</span>
                  <span className="font-bold text-slate-900 dark:text-white">
                    {Number(activeDistrictRecord.domestic_extraction_ham || 0).toLocaleString()} Ham
                  </span>
                </div>
                <div className="p-2.5 rounded bg-amber-50/60 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-800/40">
                  <Factory className="w-4 h-4 text-amber-600 mx-auto mb-1" />
                  <span className="text-[10px] text-slate-500 uppercase block">Industrial</span>
                  <span className="font-bold text-slate-900 dark:text-white">
                    {Number(activeDistrictRecord.industrial_extraction_ham || 0).toLocaleString()} Ham
                  </span>
                </div>
              </div>
            </div>

            {/* Multi-Year Trend for this District */}
            <div className="bg-white dark:bg-slate-800/80 p-4 rounded-lg border border-slate-200 dark:border-slate-700 space-y-2">
              <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider block">
                Multi-Year Trend: {selectedDistrict} (2020–2026)
              </span>
              <div className="h-36 w-full">
                {districtMultiyear?.years?.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={districtMultiyear.years} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="year" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '6px', fontSize: '11px' }}
                      />
                      <Legend wrapperStyle={{ fontSize: '10px' }} />
                      <Line type="monotone" dataKey="total_extraction_ham" name="Extraction (Ham)" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="total_recharge_ham" name="Recharge (Ham)" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                    Loading multi-year district profile...
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
            Annual Groundwater Recharge
          </span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-1">
            {totalRecharge === null ? 'Not available' : totalRecharge.toLocaleString(undefined, { maximumFractionDigits: 2 })} {totalRecharge !== null && <span className="text-xs font-normal text-slate-500">Ham</span>}
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">Cycle {year} National Aggregate</span>
        </div>

        <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
            Annual Groundwater Extraction
          </span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-1">
            {totalExtraction === null ? 'Not available' : totalExtraction.toLocaleString(undefined, { maximumFractionDigits: 2 })} {totalExtraction !== null && <span className="text-xs font-normal text-slate-500">Ham</span>}
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">Cycle {year} National Aggregate</span>
        </div>

        <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
            Extractable Resources
          </span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-1">
            {totalExtractable === null ? 'Not available' : totalExtractable.toLocaleString(undefined, { maximumFractionDigits: 2 })} {totalExtractable !== null && <span className="text-xs font-normal text-slate-500">Ham</span>}
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">Net sustainable availability</span>
        </div>

        <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
            Over-Exploited Units ({selectedState})
          </span>
          <div className="text-xl sm:text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">
            {overExploitedCount} <span className="text-xs font-normal text-slate-500">Districts</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">Stage of extraction &gt; 100%</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* State Comparison Bar Chart (2 cols) */}
        <div className="lg:col-span-2 bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
            <div>
              <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider block">
                State-wise Groundwater Resource Comparison
              </span>
              <span className="text-[11px] text-slate-500">Recharge vs Extraction by State (Cycle {year}) in Ham</span>
            </div>
          </div>

          <div className="h-72 w-full">
            {stateComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stateComparison} margin={{ top: 10, right: 10, left: 0, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="state" stroke="#64748b" fontSize={10} angle={-30} textAnchor="end" />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '6px', color: '#0f172a', fontSize: '11px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  <Bar dataKey="total_recharge_ham" name="Recharge (Ham)" fill="#0d9488" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="total_extraction_ham" name="Extraction (Ham)" fill="#2563eb" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                Loading state comparison data...
              </div>
            )}
          </div>
        </div>

        {/* Assessment Category Donut Chart (1 col) */}
        <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg p-5 shadow-2xs space-y-3">
          <div className="border-b border-slate-100 dark:border-slate-800 pb-2">
            <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider block">
              Assessment Categories ({selectedState})
            </span>
            <span className="text-[11px] text-slate-500">GEC-2015 Category Distribution in Cycle {year}</span>
          </div>

          <div className="h-48 w-full">
            {categoryDist.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryDist}
                    dataKey="count"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={65}
                    paddingAngle={3}
                  >
                    {categoryDist.map((entry) => (
                      <Cell
                        key={entry.category}
                        fill={CATEGORY_COLORS[entry.category] || '#64748b'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderRadius: '6px', color: '#0f172a', fontSize: '11px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                No category data available.
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
            {categoryDist.map((c) => (
              <div key={c.category} className="flex items-center space-x-1.5">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: CATEGORY_COLORS[c.category] || '#64748b' }}
                />
                <span className="text-slate-600 dark:text-slate-400 truncate">{c.category}:</span>
                <span className="font-semibold text-slate-900 dark:text-white">{c.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* District Drilldown Table */}
      <div className="bg-white dark:bg-[#111c2e] border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">
              District Assessment Profile: {selectedState} (Cycle {year})
            </h2>
            <p className="text-xs text-slate-500">
              Showing {filteredDistricts.length} of {districtData.length} districts in {selectedState}
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            {selectedDistrict !== 'ALL' && (
              <button
                onClick={() => setSelectedDistrict('ALL')}
                className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 text-blue-600 rounded text-xs font-semibold hover:bg-slate-200"
              >
                Clear Selection
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 uppercase font-semibold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="px-4 py-2.5">District</th>
                <th className="px-4 py-2.5 text-right">Recharge (Ham)</th>
                <th className="px-4 py-2.5 text-right">Extractable (Ham)</th>
                <th className="px-4 py-2.5 text-right">Extraction (Ham)</th>
                <th className="px-4 py-2.5 text-right">Stage of Extraction</th>
                <th className="px-4 py-2.5 text-center">Category</th>
                <th className="px-4 py-2.5 text-center">Status</th>
                <th className="px-4 py-2.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredDistricts.length > 0 ? (
                filteredDistricts.map((d) => (
                  <tr
                    key={d.district}
                    className={`transition-colors ${
                      selectedDistrict === d.district
                        ? 'bg-blue-50/80 dark:bg-blue-950/40 font-semibold'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-white flex items-center space-x-1.5">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      <span>{d.district}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">
                      {Number(d.total_annual_recharge_ham || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">
                      {Number(d.annual_extractable_groundwater_ham || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">
                      {Number(d.total_annual_extraction_ham || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium text-slate-900 dark:text-white">
                      {d.stage_of_extraction_pct ? `${d.stage_of_extraction_pct}%` : 'N/A'}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${
                        d.assessment_category === 'Safe'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                          : d.assessment_category === 'Semi-Critical'
                          ? 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
                          : d.assessment_category === 'Critical'
                          ? 'bg-orange-50 text-orange-800 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800'
                          : 'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800'
                      }`}>
                        {d.assessment_category || 'Assessed'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${
                        d.is_verified
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                      }`}>
                        {d.is_verified ? 'VERIFIED' : 'OFFICIAL'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <button
                        onClick={() => setSelectedDistrict(d.district)}
                        className="text-[11px] text-blue-600 hover:text-blue-800 dark:text-blue-400 font-semibold"
                      >
                        {selectedDistrict === d.district ? 'Selected' : 'Select'}
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" className="px-4 py-6 text-center text-slate-400">
                    No records found matching filter criteria in {selectedState} for Cycle {year}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
