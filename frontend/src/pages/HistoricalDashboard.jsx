import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Calendar,
  Layers,
  ArrowRight,
  Droplets,
  AlertCircle,
  CheckCircle2,
  Filter,
  BarChart2,
  MapPin,
  Clock
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { getStates, getDistricts, getAssessmentYears, getHistoricalTrend, compareAssessmentYears } from '../services/api';

export default function HistoricalDashboard() {
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState('Bihar');
  const [districts, setDistricts] = useState([]);
  const [selectedDistrict, setSelectedDistrict] = useState('Patna');
  const [parameter, setParameter] = useState('extraction');
  const [trendData, setTrendData] = useState(null);
  const [provenance, setProvenance] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [availableYears, setAvailableYears] = useState(['2025']);
  const [compYear1, setCompYear1] = useState('2025');
  const [compYear2, setCompYear2] = useState('2025');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAssessmentYears()
      .then((res) => {
        const years = res.data.assessment_years || [];
        setAvailableYears(years);
        if (years.length > 0) {
          setCompYear1((current) => years.includes(current) ? current : years[0]);
          setCompYear2((current) => years.includes(current) ? current : years[years.length - 1]);
        }
      })
      .catch((err) => console.error(err));

    getStates()
      .then((res) => setStates(res.data.states || []))
      .catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    if (!selectedState) return;
    getDistricts(selectedState)
      .then((res) => {
        const dists = res.data.districts || [];
        setDistricts(dists);
        if (dists.length > 0 && !dists.includes(selectedDistrict)) {
          setSelectedDistrict(dists[0]);
        }
      })
      .catch((err) => console.error(err));
  }, [selectedState]);

  useEffect(() => {
    if (!selectedState) return;
    setLoading(true);
    setError(null);

    Promise.all([
      getHistoricalTrend(selectedState, selectedDistrict || null, parameter),
      availableYears.length > 1
        ? compareAssessmentYears(selectedState, compYear1, compYear2, selectedDistrict || null, parameter)
        : Promise.resolve({ data: { data: null } }),
    ])
      .then(([trendRes, compRes]) => {
        setTrendData(trendRes.data.data);
        setProvenance(trendRes.data.provenance || []);
        setComparison(compRes.data.data);
      })
      .catch((err) => {
        console.error(err);
        setError('Failed to load historical comparison data.');
      })
      .finally(() => setLoading(false));
  }, [selectedState, selectedDistrict, parameter, compYear1, compYear2, availableYears]);

  const history = trendData?.history || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header Banner - Clean Professional Portal Style */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">
              <Calendar className="w-4 h-4" />
              <span>Multi-Year Temporal Analysis</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Historical Groundwater Trends & Assessment Cycles
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
              Track values only for individually verified district records. Year comparisons appear only when multiple verified assessment years are available.
            </p>
          </div>

          <div className="flex items-center space-x-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3.5 py-2 shrink-0">
            <Droplets className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <div className="text-xs">
              <div className="font-semibold text-slate-800 dark:text-slate-200">{availableYears.length} Verified Assessment Years</div>
              <div className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">{availableYears.join(', ') || 'None'}</div>
            </div>
          </div>
        </div>
      </div>

      {provenance.length > 0 && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50/70 dark:bg-amber-950/20 px-4 py-3 text-xs text-slate-600 dark:text-slate-300 space-y-1">
          <div className="font-semibold text-slate-800 dark:text-slate-200">Data provenance</div>
          {provenance.map((source) => (
            <div key={source.assessment_year}>
              Assessment year: {source.assessment_year}
              {' · '}Publication year: {source.publication_year || 'Not specified'}
              {' · '}Data year: {source.data_year || 'Not specified in source metadata'}
              {' · '}Individual record verified; complete source file not verified.
              {source.verified_fields?.length > 0 && (
                <> Verified measures: {source.verified_fields.join(', ')}.</>
              )}
              {source.source_document_url && (
                <>
                  {' '}
                  <a
                    href={source.source_document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {source.source_document}
                  </a>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Control Bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-xs grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* State */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">State / UT</label>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
          >
            {states.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {/* District */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">District</label>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
          >
            {districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        {/* Parameter */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">Parameter</label>
          <select
            value={parameter}
            onChange={(e) => setParameter(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
          >
            <option value="extraction">Total Extraction (Ham)</option>
            <option value="recharge">Annual Recharge (Ham)</option>
            <option value="extractable">Extractable Resources (Ham)</option>
            <option value="stage">Stage of Extraction (%)</option>
          </select>
        </div>

        {/* Baseline Year */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">Baseline Year</label>
          <select
            value={compYear1}
            onChange={(e) => setCompYear1(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
          >
            {availableYears.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {/* Comparison Year */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">Comparison Year</label>
          <select
            value={compYear2}
            onChange={(e) => setCompYear2(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
          >
            {availableYears.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Comparison Callout Cards (Tableau / Government Portal Style) */}
      {comparison && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{compYear1} Baseline</div>
            <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {Number(comparison.year_1?.value || 0).toLocaleString()} <span className="text-xs font-normal text-slate-500">{comparison.unit}</span>
            </div>
            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium mt-1">{comparison.district || comparison.state} ({compYear1})</div>
          </div>

          <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{compYear2} Value</div>
            <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {Number(comparison.year_2?.value || 0).toLocaleString()} <span className="text-xs font-normal text-slate-500">{comparison.unit}</span>
            </div>
            <div className="text-xs text-teal-600 dark:text-teal-400 font-medium mt-1">{comparison.district || comparison.state} ({compYear2})</div>
          </div>

          <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Absolute Delta</div>
            <div className={`text-xl sm:text-2xl font-bold mt-1 ${
              comparison.difference > 0 ? 'text-amber-600 dark:text-amber-400' : comparison.difference < 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-700 dark:text-slate-300'
            }`}>
              {comparison.difference > 0 ? `+${comparison.difference.toLocaleString()}` : comparison.difference?.toLocaleString()} <span className="text-xs font-normal text-slate-500">{comparison.unit}</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">Net difference between cycles</div>
          </div>

          <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Relative Change</div>
            <div className={`text-xl sm:text-2xl font-bold mt-1 ${
              comparison.percent_change > 0 ? 'text-amber-600 dark:text-amber-400' : comparison.percent_change < 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-700 dark:text-slate-300'
            }`}>
              {comparison.percent_change > 0 ? `+${comparison.percent_change}%` : `${comparison.percent_change}%`}
            </div>
            <div className="text-xs text-slate-500 mt-1">Trend: <span className="capitalize font-semibold text-slate-700 dark:text-slate-300">{comparison.trend}</span></div>
          </div>
        </div>
      )}

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Area Trend Chart */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-xs space-y-3">
          <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-700 pb-3">
            <div>
              <h2 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Multi-Cycle Trajectory (2020 – 2026)
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">{selectedDistrict}, {selectedState} • {parameter.toUpperCase()}</p>
            </div>
            <span className="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-semibold px-2.5 py-0.5 rounded-md border border-blue-200 dark:border-blue-800">
              Trajectory
            </span>
          </div>

          <div className="h-64 w-full">
            {history.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', color: '#0f172a', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Area
                    type="monotone"
                    dataKey={
                      parameter === 'recharge'
                        ? 'recharge_ham'
                        : parameter === 'extractable'
                        ? 'extractable_ham'
                        : parameter === 'stage'
                        ? 'stage_of_extraction_pct'
                        : 'extraction_ham'
                    }
                    stroke="#2563eb"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#trendGradient)"
                    name={parameter}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                No trend data available for this selection.
              </div>
            )}
          </div>
        </div>

        {/* Recharge vs Extraction Balance */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-xs space-y-3">
          <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-700 pb-3">
            <div>
              <h2 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Recharge vs Extraction Balance
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Volumetric comparison across cycles (Hectare Meter - Ham)</p>
            </div>
            <span className="bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 text-xs font-semibold px-2.5 py-0.5 rounded-md border border-teal-200 dark:border-teal-800">
              Sustainability
            </span>
          </div>

          <div className="h-64 w-full">
            {history.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={history} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', color: '#0f172a', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
                  <Bar dataKey="recharge_ham" fill="#0d9488" name="Annual Recharge (Ham)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="extraction_ham" fill="#e11d48" name="Annual Extraction (Ham)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                No data available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Historical Data Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">
              Assessment Cycle Records for {selectedDistrict}, {selectedState}
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Verified tabular data retrieved from groundwater database</p>
          </div>
          <span className="text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/30 px-2.5 py-0.5 rounded-md border border-blue-200 dark:border-blue-800">
            {history.length} Cycles Reported
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 uppercase font-semibold text-[11px] tracking-wider border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-4 py-3">Assessment Cycle</th>
                <th className="px-4 py-3 text-right">Recharge (Ham)</th>
                <th className="px-4 py-3 text-right">Extractable (Ham)</th>
                <th className="px-4 py-3 text-right">Extraction (Ham)</th>
                <th className="px-4 py-3 text-right">Stage of Extraction (%)</th>
                <th className="px-4 py-3 text-center">GEC-2015 Category</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {history.map((row) => (
                <tr key={row.year} className="hover:bg-slate-50/80 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">{row.year}</td>
                  <td className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    {Number(row.recharge_ham || 0).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    {Number(row.extractable_ham || 0).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    {Number(row.extraction_ham || 0).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-900 dark:text-white">
                    {row.stage_of_extraction_pct ? `${row.stage_of_extraction_pct}%` : 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                        row.category === 'Safe'
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                          : row.category === 'Semi-Critical'
                          ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                          : row.category === 'Critical'
                          ? 'bg-orange-50 dark:bg-orange-950/40 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-800'
                          : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                      }`}
                    >
                      {row.category || 'Monitored'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
