import React, { useState, useEffect } from 'react';
import {
  Database,
  ExternalLink,
  FileSpreadsheet,
  Calendar,
  MapPin,
  CheckCircle,
  Layers,
  Droplets,
  BookOpen
} from 'lucide-react';
import { getSources } from '../services/api';

export default function DataSourcesPage() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const verifiedRecordCount = sources.reduce(
    (total, source) => total + (source.verified_record_count || 0),
    0
  );

  useEffect(() => {
    getSources()
      .then((res) => setSources(res.data.sources || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">
              <Database className="w-4 h-4" />
              <span>Data Provenance & Source Catalog</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Official Data Sources & Ingestion Catalog
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
              Local source files are not treated as verified by default. Only individually verified records are available to queries; assessment year, publication year, data year, and source document are shown separately when known.
            </p>
          </div>
          <span className="px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-medium flex items-center space-x-1.5 shrink-0">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>{verifiedRecordCount} individually verified records</span>
          </span>
        </div>
      </div>

      {/* Dataset Summary Metrics (BetterGov Style) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-xs">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Verified Records</span>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{verifiedRecordCount}</div>
          <p className="text-[11px] text-slate-500 mt-0.5">Individual district records</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-xs">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Primary Agency</span>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">CGWB</div>
          <p className="text-[11px] text-slate-500 mt-0.5">Central Ground Water Board</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-xs">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Measurement Unit</span>
          <div className="text-2xl font-bold text-teal-600 dark:text-teal-400 mt-1">Ham</div>
          <p className="text-[11px] text-slate-500 mt-0.5">1 Ham = 10,000 cubic meters</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-xs">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Database Storage</span>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">SQLite</div>
          <p className="text-[11px] text-slate-500 mt-0.5">Relational schema with indexing</p>
        </div>
      </div>

      {/* Dataset Cards */}
      <div className="space-y-4">
        {sources.map((src) => (
          <div
            key={src.id}
            className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-xs space-y-4"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-700">
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">{src.name}</h2>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border flex items-center space-x-1 ${
                    src.is_verified
                      ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                      : src.verified_record_count > 0
                      ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800'
                      : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                  }`}>
                    <CheckCircle className="w-3 h-3" />
                    <span>{src.is_verified ? 'Verified dataset' : src.verified_record_count > 0 ? 'Some records verified' : 'Unverified dataset'}</span>
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{src.source_agency}</p>
              </div>

              {src.source_url && (
                <a
                  href={src.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1.5 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 px-3 py-1.5 rounded-lg text-xs font-medium border border-blue-200 dark:border-blue-800 transition-colors w-fit"
                >
                  <span>Open source document</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            {/* Grid of metadata attributes */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Assessment Period</span>
                <span className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm mt-0.5 block">{src.assessment_period}</span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Publication Year</span>
                <span className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm mt-0.5 block">{src.publication_year || 'Not specified'}</span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Data Year</span>
                <span className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm mt-0.5 block">{src.data_year || 'Not specified'}</span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Data Format</span>
                <span className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm mt-0.5 block">{src.data_format}</span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Unit</span>
                <span className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm mt-0.5 block">{src.unit}</span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Geographic Scope</span>
                <span className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm mt-0.5 block">National Coverage</span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Ingested Records</span>
                <span className="font-semibold text-blue-600 dark:text-blue-400 text-xs sm:text-sm mt-0.5 block">
                  {src.verified_record_count || 0} / {src.num_records}
                </span>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-semibold uppercase text-slate-500 block">Status</span>
                <span className={`font-semibold text-xs mt-0.5 block ${
                  src.is_verified ? 'text-emerald-600 dark:text-emerald-400' :
                    src.verified_record_count > 0 ? 'text-amber-600 dark:text-amber-400' :
                      'text-slate-600 dark:text-slate-400'
                }`}>
                  {src.is_verified ? 'Verified' : src.verified_record_count > 0 ? 'Partially verified' : 'Unverified'}
                </span>
              </div>
            </div>

            {/* Hydrogeological Data Notes */}
            <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-400 space-y-1.5 leading-relaxed">
              <span className="font-semibold text-slate-800 dark:text-slate-200 text-xs block">
                Groundwater Estimation Committee (GEC-2015) Methodology Notes
              </span>
              <p>
                Dynamic Ground Water Resource Assessment in India is conducted jointly by the Central Ground Water Board (CGWB)
                and State Ground Water Departments. Assessment units are categorized based on the Stage of Ground Water Extraction (SOE):
              </p>
              <ul className="list-disc pl-5 space-y-0.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                <li><strong className="text-emerald-600 dark:text-emerald-400">Safe:</strong> Stage of Extraction &le; 70% with no significant long-term decline.</li>
                <li><strong className="text-amber-600 dark:text-amber-400">Semi-Critical:</strong> Stage of Extraction &gt; 70% and &le; 90%.</li>
                <li><strong className="text-orange-600 dark:text-orange-400">Critical:</strong> Stage of Extraction &gt; 90% and &le; 100%.</li>
                <li><strong className="text-rose-600 dark:text-rose-400">Over-Exploited:</strong> Stage of Extraction &gt; 100% (extraction exceeds annual replenishable recharge).</li>
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
