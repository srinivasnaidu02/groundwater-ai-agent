import React, { useState } from 'react';
import { useLocation, NavLink } from 'react-router-dom';
import { Menu, Droplets, ChevronRight } from 'lucide-react';
import Sidebar from './Sidebar';

export default function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const isRootPage = location.pathname === '/' || location.pathname === '/analyst';

  return (
    <div className="min-h-screen bg-[#07131e] text-slate-100 flex flex-col font-sans">
      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        drawerMode={isRootPage}
      />

      {/* Slim Top Bar for Root Page (INGRES Target Design) */}
      {isRootPage ? (
        <header className="h-14 bg-[#07131e] border-b border-slate-800/80 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="p-1.5 rounded-lg bg-[#0b1a2d] border border-slate-700/80 text-slate-300 hover:text-white hover:border-teal-500 transition-colors cursor-pointer"
              title="Open Navigation Menu"
            >
              <Menu className="w-5 h-5 text-teal-400" />
            </button>
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-400 shadow-xs">
                <Droplets className="w-4 h-4 text-teal-400" />
              </div>
              <span className="font-bold text-sm tracking-tight text-white">
                INGRES Groundwater AI
              </span>
              <span className="hidden sm:inline-block text-[10px] bg-teal-500/10 text-teal-300 border border-teal-500/30 px-2 py-0.5 rounded-full font-medium">
                National Portal
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <NavLink
              to="/analytics"
              className="hidden sm:flex items-center gap-1 text-slate-400 hover:text-teal-300 transition-colors px-2 py-1"
            >
              <span>Analytics Dashboard</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </NavLink>
          </div>
        </header>
      ) : (
        /* Floating mobile toggle button for other pages */
        <button
          onClick={() => setMobileOpen(true)}
          className="lg:hidden fixed top-3 left-3 z-40 p-2 rounded-lg bg-[#07131e]/90 border border-slate-800 text-slate-300 hover:text-white"
          title="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      {/* Main Content Area */}
      <div
        className={`flex-1 flex flex-col transition-all duration-200 ${
          isRootPage ? 'w-full' : (collapsed ? 'lg:pl-16' : 'lg:pl-60')
        }`}
      >
        <main className="flex-1 overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
