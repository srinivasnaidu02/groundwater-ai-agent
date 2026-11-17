import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Globe,
  FileText,
  CheckCircle2,
  Database,
  Info,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Droplets,
  Sparkles,
  X
} from 'lucide-react';

export default function Sidebar({ collapsed, setCollapsed, mobileOpen, setMobileOpen }) {
  const [workspaceOpen, setWorkspaceOpen] = useState(true);
  const [knowledgeOpen, setKnowledgeOpen] = useState(true);
  const [systemOpen, setSystemOpen] = useState(true);

  const sections = [
    {
      title: 'WORKSPACE',
      open: workspaceOpen,
      setOpen: setWorkspaceOpen,
      items: [
        { to: '/', label: 'AI Analyst (ReAct)', icon: Sparkles },
        { to: '/analytics', label: 'Analytics Dashboard', icon: BarChart3 },
        { to: '/historical', label: 'Historical Analysis', icon: TrendingUp },
        { to: '/coverage', label: 'National Coverage', icon: Globe },
      ]
    },
    {
      title: 'KNOWLEDGE & TRUST',
      open: knowledgeOpen,
      setOpen: setKnowledgeOpen,
      items: [
        { to: '/supported-queries', label: 'Supported Queries', icon: FileText },
        { to: '/evaluation', label: 'Evaluation Benchmark', icon: CheckCircle2 },
        { to: '/data-sources', label: 'Data Provenance', icon: Database },
      ]
    },
    {
      title: 'SYSTEM',
      open: systemOpen,
      setOpen: setSystemOpen,
      items: [
        { to: '/about', label: 'About Platform', icon: Info },
        { to: '/settings', label: 'Settings', icon: Settings },
      ]
    }
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col transition-all duration-200 ease-in-out border-r
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          ${collapsed ? 'w-16' : 'w-60'}
          bg-[#07131e] border-slate-800/80 text-slate-300 shadow-xl select-none`}
      >
        {/* Brand Header */}
        <div className="h-14 flex items-center justify-between px-3.5 border-b border-slate-800/80 bg-[#06101a]">
          <NavLink to="/" className="flex items-center space-x-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-600 text-white flex items-center justify-center shrink-0 shadow-md shadow-cyan-900/40">
              <Droplets className="w-4 h-4 text-cyan-100" />
            </div>
            {!collapsed && (
              <div className="flex flex-col min-w-0">
                <span className="font-bold text-sm tracking-tight text-white truncate">
                  Groundwater AI
                </span>
                <span className="text-[10px] text-cyan-400/80 font-medium truncate tracking-wide">
                  National Data Portal
                </span>
              </div>
            )}
          </NavLink>

          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden text-slate-400 hover:text-white p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Sections */}
        <nav className="flex-1 py-3 px-2 space-y-4 overflow-y-auto">
          {sections.map((sec, idx) => (
            <div key={idx} className="space-y-1">
              {!collapsed && (
                <button
                  type="button"
                  onClick={() => sec.setOpen(!sec.open)}
                  className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold tracking-wider text-slate-400/90 hover:text-slate-200 uppercase transition-colors"
                >
                  <span>{sec.title}</span>
                  {sec.open ? (
                    <ChevronDown className="w-3 h-3 text-slate-500" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-slate-500" />
                  )}
                </button>
              )}

              {(collapsed || sec.open) && (
                <div className="space-y-0.5">
                  {sec.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        onClick={() => setMobileOpen(false)}
                        title={collapsed ? item.label : undefined}
                        className={({ isActive }) =>
                          `flex items-center space-x-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all
                          ${
                            isActive
                              ? 'bg-gradient-to-r from-blue-600/90 to-cyan-600/80 text-white font-semibold shadow-sm shadow-cyan-500/20'
                              : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                          }
                          ${collapsed ? 'justify-center px-0' : ''}`
                        }
                      >
                        <Icon className="w-4 h-4 shrink-0 text-cyan-300/80" />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* Bottom Collapse Toggle & Version */}
        <div className="p-2.5 border-t border-slate-800/80 bg-[#06101a] flex items-center justify-between">
          {!collapsed && (
            <span className="text-[11px] text-slate-500 font-mono pl-1">
              v2.4 • CGWB / IN-GRES
            </span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={`hidden lg:flex items-center justify-center p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors
              ${collapsed ? 'w-full' : ''}`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </aside>
    </>
  );
}