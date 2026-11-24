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

export const getStates = (year = null) =>
  api.get(`/meta/states${year ? `?year=${encodeURIComponent(year)}` : ''}`);
export const getDistricts = (state, year = null) =>
  api.get(`/meta/districts?state=${encodeURIComponent(state)}${year ? `&year=${encodeURIComponent(year)}` : ''}`);
export const getAssessmentYears = () => api.get('/meta/years');
export const getYears = () => api.get('/meta/years');
export const getMetaYears = () => api.get('/meta/years');
export const getMetaStates = (year = null) =>
  api.get(`/meta/states${year ? `?year=${encodeURIComponent(year)}` : ''}`);
export const getMetaDistricts = (state, year = null) =>
  api.get(`/meta/districts?state=${encodeURIComponent(state)}${year ? `&year=${encodeURIComponent(year)}` : ''}`);
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
export const queryAgent = (queryOrParams, mode = 'auto', year = null, state = null, district = null) => {
  if (typeof queryOrParams === 'object' && queryOrParams !== null) {
    const q = queryOrParams.query || queryOrParams.question;
    return api.post('/agent/query', {
      query: q,
      mode: queryOrParams.mode || 'auto',
      year: queryOrParams.year ? parseInt(queryOrParams.year, 10) : null,
      state: queryOrParams.state || null,
      district: (queryOrParams.district && queryOrParams.district !== 'State-level (no district)') ? queryOrParams.district : null,
    });
  }
  const cleanDistrict = (district && district !== 'State-level (no district)') ? district : null;
  const cleanYear = year ? parseInt(year, 10) : null;
  return api.post('/agent/query', { query: queryOrParams, mode, year: cleanYear, state, district: cleanDistrict });
};
export const getAgentStatus = () => api.get('/agent/status');

export default api;
