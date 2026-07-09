export interface User {
  id: string;
  name: string;
  email: string;
  profile_image?: string;
  account_type: "free" | "pro" | "enterprise";
  role: "user" | "admin";
  is_verified: boolean;
  created_at: string;
}

export interface StockQuote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap: number;
  high: number;
  low: number;
}

export interface HistoricalBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Prediction {
  symbol: string;
  signal: "BUY" | "SELL" | "HOLD";
  confidence_score: number;
  predicted_price: number;
  predicted_prices: number[];
  current_price: number;
  trend: "bullish" | "bearish";
  indicators: {
    rsi?: number;
    macd?: number;
    ma20?: number;
    ma50?: number;
    bb_upper?: number;
    bb_lower?: number;
  };
}

export interface PortfolioItem {
  id: string;
  stock_symbol: string;
  allocation_percentage: number;
  average_buy_price: number;
  quantity: number;
  expected_return: number;
  risk_score: number;
}

export interface RiskAnalysis {
  symbol: string;
  volatility: number;
  var_95: number;
  var_99: number;
  max_drawdown: number;
  beta: number;
  risk_score: number;
  stop_loss_recommendation: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
}

export interface NewsArticle {
  title: string;
  description?: string;
  url: string;
  source: string;
  published_at: string;
  image?: string;
  sentiment: "positive" | "negative" | "neutral";
  sentiment_score: number;
}

export interface ChatMessage {
  id: string;
  prompt: string;
  response: string;
  created_at: string;
}

export interface Trade {
  id: string;
  stock_symbol: string;
  trade_type: "buy" | "sell";
  quantity: number;
  amount: number;
  timestamp: string;
}
