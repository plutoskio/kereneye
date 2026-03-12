import { API_BASE_URL } from '../config';

const API = API_BASE_URL;

async function parseJson(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    optional = false,
    errorMessage,
  } = options;

  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const payload = await parseJson(response);

  if (optional && response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      payload?.detail ||
      payload?.message ||
      errorMessage ||
      `Request failed (${response.status})`
    );
  }

  return payload;
}

export function getCompany(symbol) {
  return request(`/api/company/${symbol}`, {
    errorMessage: 'Company not found.',
  });
}

export function getResearchReport(symbol) {
  return request(`/api/research/${symbol}`, { optional: true });
}

export async function getResearchStatus(symbol) {
  const data = await request(`/api/research/status/${symbol}`, { optional: true });
  return data?.status || '';
}

export function generateResearchReport(symbol) {
  return request(`/api/research/${symbol}`, {
    method: 'POST',
    errorMessage: 'Failed to generate report.',
  });
}

export function getNewsAnalysis(symbol) {
  return request(`/api/news_analysis/${symbol}`, { optional: true });
}

export async function getNewsAnalysisStatus(symbol) {
  const data = await request(`/api/news_analysis/status/${symbol}`, { optional: true });
  return data?.status || '';
}

export function generateNewsAnalysis(symbol) {
  return request(`/api/news_analysis/${symbol}`, {
    method: 'POST',
    errorMessage: 'Failed to generate news analysis.',
  });
}

export function getPortfolioSummary() {
  return request('/api/portfolio/summary');
}

export function getPortfolioPerformance(period) {
  return request(`/api/portfolio/performance?period=${encodeURIComponent(period)}`);
}

export async function getPortfolioMarketStatus() {
  const data = await request('/api/portfolio/market-status');
  return data?.markets || [];
}

export function getMarketOverview() {
  return request('/api/market/overview');
}

export function getMarketBrief() {
  return request('/api/market/brief', { optional: true });
}

export async function getMarketBriefStatus() {
  const data = await request('/api/market/brief/status', { optional: true });
  return data?.status || '';
}

export function generateMarketBrief() {
  return request('/api/market/brief', {
    method: 'POST',
    errorMessage: 'Failed to generate brief.',
  });
}

export async function getPortfolioNews() {
  const data = await request('/api/portfolio/news');
  return data?.holdings_news || [];
}

export async function getPortfolioNewsReportStatus() {
  const data = await request('/api/portfolio/news/analyze/status', { optional: true });
  return data?.status || '';
}

export function generatePortfolioNewsReport() {
  return request('/api/portfolio/news/analyze', {
    method: 'POST',
    errorMessage: 'Failed to generate AI news report.',
  });
}

export function addPortfolioHolding(payload) {
  return request('/api/portfolio/holdings', {
    method: 'POST',
    body: payload,
    errorMessage: 'Failed to add holding.',
  });
}

export function sellPortfolioHolding(ticker, payload) {
  return request(`/api/portfolio/holdings/${ticker}/sell`, {
    method: 'POST',
    body: payload,
    errorMessage: 'Failed to sell holding.',
  });
}

export function setPortfolioCash(payload) {
  return request('/api/portfolio/cash', {
    method: 'POST',
    body: payload,
    errorMessage: 'Failed to update cash.',
  });
}

export async function getTransactions() {
  const data = await request('/api/portfolio/transactions');
  return data?.transactions || [];
}
