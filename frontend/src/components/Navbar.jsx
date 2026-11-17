import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Droplets, MessageSquare, BarChart3, Database, ShieldCheck, BookOpen, Activity, TrendingUp, Globe } from 'lucide-react';
import { getHealth } from '../services/api';

export default function Navbar() {
  const [health, setHealth] = useState({ status: 'connecting', total_records: 0 });

  useEffect(() => {
    getHealth()
      .then((res) => setHealth(res.data))
      .catch(() => setHealth({ status: 'offline', total_records: 0 }));
  }, []);

  const navItems = [
    { to: '/', label: 'Query Agent', icon: MessageSquare },
    { to: '/historical', label: 'Historical (2020-26)', icon: TrendingUp },
    { to: '/coverage', label: 'National Coverage', icon: Globe },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/evaluation', label: 'Benchmark', icon: ShieldCheck },
    { to: '/data-sources', label: 'Provenance', icon: Database },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-tr from-sky-600 to-teal-500 p-2.5 rounded-xl shadow-xs text-white">
              <Droplets className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl tracking-tight text-slate-900">GROUNDWATER AI</span>
                <span className="bg-sky-100 text-sky-800 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">IN-GRES Data</span>
              </div>
              <p className="text-xs text-slate-500 font-medium hidden sm:block">
                Natural Language Groundwater Database Query Agent
              </p>
            </div>
          </div>

          <nav className="hidden md:flex space-x-1 lg:space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-sky-50 text-sky-700 shadow-xs border border-sky-100 font-semibold'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          <div className="flex items-center space-x-2.5">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border bg-slate-50 border-slate-200 text-slate-700">
              <span
                className={`w-2 h-2 rounded-full ${
                  health.status === 'healthy'
                    ? 'bg-emerald-500'
                    : health.status === 'connecting'
                    ? 'bg-amber-400 animate-ping'
                    : 'bg-rose-500'
                }`}
              />
              <span className="capitalize">{health.status}</span>
              {health.total_records > 0 && (
                <span className="text-slate-400 font-mono text-[11px]">({health.total_records} records)</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile nav */}
      <div className="md:hidden border-t border-slate-200 px-2 py-1.5 flex overflow-x-auto space-x-1 bg-slate-50 text-xs">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `whitespace-nowrap px-3 py-1.5 rounded-md font-medium ${
                isActive ? 'bg-sky-600 text-white' : 'text-slate-600'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </header>
  );
}

