import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  CheckCircle,
  XCircle,
  Play,
  Database,
  Layers,
  ArrowRight,
  Search,
  Code
} from 'lucide-react';
import { getFunctions } from '../services/api';

export default function SupportedQueriesPage() {
  const [functions, setFunctions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('All');
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    getFunctions()
      .then((res) => setFunctions(res.data.functions || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const categories = ['All', ...new Set(functions.map((f) => f.category))];

  const filteredFunctions = functions.filter((fn) => {
    const matchesCategory = activeCategory === 'All' || fn.category === activeCategory;
    const matchesSearch =
      fn.function_name.toLowerCase().includes(search.toLowerCase()) ||
      fn.description.toLowerCase().includes(search.toLowerCase()) ||
      (fn.example_question || '').toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleTry = (example) => {
    navigate(`/?q=${encodeURIComponent(example)}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">
              <Compass className="w-4 h-4" />
              <span>Function Registry</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Supported Queries & Function Dispatch Catalog
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
              Every natural language question deterministically maps to a verified database function. The agent executes parameterized repository queries to retrieve ground-truth records.
            </p>
          </div>
          <span className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-mono font-medium shrink-0">
            {functions.length} Registered Functions
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Categories Pills */}
        <div className="flex overflow-x-auto space-x-1.5 pb-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeCategory === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search function or topic..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Function Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredFunctions.map((fn) => (
          <div
            key={fn.function_name}
            className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-blue-300 dark:hover:border-blue-600 transition-colors space-y-3"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-semibold text-blue-700 dark:text-blue-300 text-xs bg-slate-50 dark:bg-slate-900 px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-700">
                    {fn.function_name}()
                  </span>
                  <span className="text-[10px] font-medium uppercase px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                    {fn.category}
                  </span>
                </div>

                {fn.data_available ? (
                  <span className="inline-flex items-center space-x-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                    <CheckCircle className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                    <span>Available</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1 text-[11px] font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded-full border border-rose-200 dark:border-rose-800">
                    <XCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                    <span>Unavailable Guard</span>
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mt-1.5">{fn.description}</p>

              <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-700 space-y-1 text-xs">
                <div className="flex items-center space-x-2 font-mono text-[11px]">
                  <span className="text-slate-500 w-24 shrink-0">Required:</span>
                  <span className="text-slate-800 dark:text-slate-200 font-medium">
                    {fn.required_parameters.length > 0 ? fn.required_parameters.join(', ') : 'None'}
                  </span>
                </div>
                <div className="flex items-center space-x-2 font-mono text-[11px]">
                  <span className="text-slate-500 w-24 shrink-0">Supported:</span>
                  <span className="text-slate-600 dark:text-slate-400">
                    {fn.parameters.length > 0 ? fn.parameters.join(', ') : 'None'}
                  </span>
                </div>
              </div>
            </div>

            {/* Clickable Example */}
            {fn.example_question && (
              <div className="pt-2.5 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <span className="text-[10px] uppercase font-semibold text-slate-500 block">Example Query:</span>
                  <span className="text-xs text-blue-700 dark:text-blue-300 font-medium italic truncate block">
                    "{fn.example_question}"
                  </span>
                </div>
                <button
                  onClick={() => handleTry(fn.example_question)}
                  className="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-medium flex items-center space-x-1 transition-colors shrink-0"
                >
                  <span>Query</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
