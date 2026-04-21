/**
 * useSimulation Hook
 * React Query hook for fetching and managing flood simulations
 * Objective: Enable 3D Cesium visualization with playback controls
 */

import {
  useMutation,
  useQuery,
  UseMutationResult,
  UseQueryResult,
} from '@tanstack/react-query';
import { SimulationResponse } from '@/types/floodguard';
import { api } from '@/lib/api';

export function useSimulation(
  countyCode: string | null,
): UseQueryResult<SimulationResponse> {
  return useQuery({
    queryKey: ['simulation', countyCode],
    queryFn: async () => {
      if (!countyCode) throw new Error('County code required');
      // Fetch 3-hour simulation, 5-min step interval
      return api.triggerSimulation(countyCode, 3, 5);
    },
    enabled: false,
    staleTime: Infinity,
    retry: 1,
  });
}

export function useTriggerSimulation(): UseMutationResult<
  SimulationResponse,
  Error,
  string
> {
  return useMutation({
    mutationFn: async (countyCode: string) => {
      return api.triggerSimulation(countyCode, 3, 5);
    },
  });
}
