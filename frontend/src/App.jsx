import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import ChatPage from './pages/ChatPage';
import AIAnalystPage from './pages/AIAnalystPage';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import HistoricalDashboard from './pages/HistoricalDashboard';
import NationalCoveragePage from './pages/NationalCoveragePage';
import SupportedQueriesPage from './pages/SupportedQueriesPage';
import EvaluationPage from './pages/EvaluationPage';
import DataSourcesPage from './pages/DataSourcesPage';
import AboutPage from './pages/AboutPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <ThemeProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/analyst" element={<AIAnalystPage />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/historical" element={<HistoricalDashboard />} />
          <Route path="/coverage" element={<NationalCoveragePage />} />
          <Route path="/supported-queries" element={<SupportedQueriesPage />} />
          <Route path="/evaluation" element={<EvaluationPage />} />
          <Route path="/data-sources" element={<DataSourcesPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </ThemeProvider>
  );
}
