import axios from 'axios';

const getBaseURL = () => {
  if (typeof window !== 'undefined') {
    return 'http://127.0.0.1:8000/api';
  }
  return '/api';
};

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
});

export const getStates = () => api.get('/states');
export const getDistricts = (state) => api.get(`/districts/${encodeURIComponent(state)}`);
export const getAssessmentYears = () => api.get('/assessment-years');
export const getHealth = () => api.get('/health');
export const getMetadata = () => api.get('/metadata');
export const getFunctions = () => api.get('/functions');
export const getQueryHistory = () => api.get('/query-history');
export const getEvaluationSummary = () => api.get('/evaluation/summary');
export const getEvaluationDetails = (limit = 105) => api.get(`/evaluation/details?limit=${limit}`);
export const getSources = () => api.get('/sources');
export const getStateComparison = (year = '2022') => api.get(`/analytics/state-comparison?year=${year}`);
export const getCategoryDistribution = (year = '2022', state = '') =>
  api.get(`/analytics/category-distribution?year=${year}${state ? `&state=${encodeURIComponent(state)}` : ''}`);
export const getDistrictData = (state, year = '2022', district = '') =>
  api.get(`/analytics/district-data/${encodeURIComponent(state)}?year=${year}${district ? `&district=${encodeURIComponent(district)}` : ''}`);
export const getDistrictMultiyear = (state, district) =>
  api.get(`/analytics/district-multiyear/${encodeURIComponent(state)}/${encodeURIComponent(district)}`);

// Multi-Year & Historical Analytics Endpoints
export const getNationalCoverage = () => api.get('/coverage');
export const getYearlyCoverage = () => api.get('/analytics/yearly-coverage');
export const getHistoricalTrend = (state, district = null, parameter = 'extraction') =>
  api.get(`/analytics/historical-trend?state=${encodeURIComponent(state)}${district ? `&district=${encodeURIComponent(district)}` : ''}&parameter=${parameter}`);
export const compareAssessmentYears = (state, year1 = '2020', year2 = '2026', district = null, parameter = 'extraction') =>
  api.get(`/analytics/compare-years?state=${encodeURIComponent(state)}&year1=${year1}&year2=${year2}${district ? `&district=${encodeURIComponent(district)}` : ''}&parameter=${parameter}`);
export const getModelComparison = () => api.get('/evaluation/model-comparison');

// Agentic & Generative AI Endpoints
export const queryAgent = (query, mode = 'auto', year = null, state = null, district = null) =>
  api.post('/agent/query', { query, mode, year, state, district });
export const getAgentStatus = () => api.get('/agent/status');

export default api;
