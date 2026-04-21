import { create } from 'zustand';
import type { AppState, RiskLevel } from '@/types/floodguard';

interface AppActions {
  setSelectedCountyCode: (countyCode: string | null) => void;
  setIsAdmin: (isAdmin: boolean) => void;
  setSimulationId: (simulationId: string | null) => void;
  addAlert: (alert: { type: RiskLevel; message: string }) => void;
  clearAlert: (id: string) => void;
  setDataFreshness: (freshness: Partial<AppState['dataFreshness']>) => void;
}

type StoreState = AppState & AppActions;

export const useAppStore = create<StoreState>((set) => ({
  selectedCountyCode: null,
  isAdmin: false,
  simulationId: null,
  alertQueue: [],
  dataFreshness: {
    lastIMERG: null,
    lastBarometerCount: 0,
  },
  setSelectedCountyCode: (selectedCountyCode) => set({ selectedCountyCode }),
  setIsAdmin: (isAdmin) => set({ isAdmin }),
  setSimulationId: (simulationId) => set({ simulationId }),
  addAlert: (alert) =>
    set((state) => ({
      alertQueue: [
        {
          id:
            typeof crypto !== 'undefined' && 'randomUUID' in crypto
              ? crypto.randomUUID()
              : `${Date.now()}-${state.alertQueue.length}`,
          ...alert,
        },
        ...state.alertQueue,
      ].slice(0, 20),
    })),
  clearAlert: (id) =>
    set((state) => ({
      alertQueue: state.alertQueue.filter((alert) => alert.id !== id),
    })),
  setDataFreshness: (freshness) =>
    set((state) => ({
      dataFreshness: {
        ...state.dataFreshness,
        ...freshness,
      },
    })),
}));
