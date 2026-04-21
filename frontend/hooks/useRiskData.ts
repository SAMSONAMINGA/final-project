/**
 * useRiskData Hook
 * React Query hook for fetching and caching risk heatmap data
 * Objective: Enable 30s refresh interval with cache invalidation strategy
 */

import {
  keepPreviousData,
  useQuery,
  UseQueryResult,
} from '@tanstack/react-query';
import { RiskHeatmapResponse } from '@/types/floodguard';
import { api } from '@/lib/api';

export function useRiskData(
  countyCode: string | null,
  enabled: boolean = true,
): UseQueryResult<RiskHeatmapResponse> {
  return useQuery<RiskHeatmapResponse>({
    queryKey: ['risk', countyCode],
    queryFn: async () => {
      if (!countyCode) throw new Error('County code required');
      return api.getRiskHeatmap(countyCode);
    },
    enabled: enabled && !!countyCode,
    // Refresh every 30 seconds to match backend Celery schedule
    refetchInterval: 30000,
    // Cache for 25s to prevent repeated requests within window
    staleTime: 25000,
    // Keep previous data while fetching new data (avoid flicker)
    placeholderData: keepPreviousData,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
}
