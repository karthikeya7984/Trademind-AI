import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function useStockQuote(symbol: string, refetchInterval = 30_000) {
  return useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.get(`/market/quote/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    refetchInterval,
  });
}

export function useStockHistory(symbol: string, period = "1y", interval = "1d") {
  return useQuery({
    queryKey: ["history", symbol, period, interval],
    queryFn: () => api.get(`/market/history/${symbol}?period=${period}&interval=${interval}`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 300_000,
  });
}

export function usePrediction(symbol: string) {
  return useQuery({
    queryKey: ["prediction", symbol],
    queryFn: () => api.get(`/predictions/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 600_000,
  });
}

export function useRiskAnalysis(symbol: string) {
  return useQuery({
    queryKey: ["risk", symbol],
    queryFn: () => api.get(`/risk/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 900_000,
  });
}
