/**
 * EKF Parameter Tuner Component (Admin only)
 * Real-time adjustment of rainfall fusion sensitivity per county
 * Objective: Enable adaptive calibration of 3-source sensor fusion (barometer + IMERG + NWP)
 */

'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { EKFTuneRequest } from '@/types/floodguard';
import { api } from '@/lib/api';
import clsx from 'clsx';
import { Save, RotateCcw } from 'lucide-react';

interface EKFTunerProps {
  countyCode: string;
}

// Default EKF parameters from backend
const DEFAULT_PARAMS = {
  pressure_sensitivity: 0.15, // mm/h per hPa/min
  process_noise_q: 0.1,
  measurement_noise_r: 0.5,
};

export function EKFTuner({ countyCode }: EKFTunerProps) {
  const [pressureSensitivity, setPressureSensitivity] = useState(
    DEFAULT_PARAMS.pressure_sensitivity,
  );
  const [processNoise, setProcessNoise] = useState(DEFAULT_PARAMS.process_noise_q);
  const [measurementNoise, setMeasurementNoise] = useState(
    DEFAULT_PARAMS.measurement_noise_r,
  );

  const tuneMutation = useMutation({
    mutationFn: async (params: EKFTuneRequest) => {
      return api.tuneEKFParameters(params);
    },
  });

  const handleReset = () => {
    setPressureSensitivity(DEFAULT_PARAMS.pressure_sensitivity);
    setProcessNoise(DEFAULT_PARAMS.process_noise_q);
    setMeasurementNoise(DEFAULT_PARAMS.measurement_noise_r);
  };

  const handleSave = async () => {
    try {
      await tuneMutation.mutateAsync({
        county_code: countyCode,
        pressure_sensitivity: pressureSensitivity,
        process_noise_q: processNoise,
        measurement_noise_r: measurementNoise,
      });
    } catch (error) {
      console.error('Failed to tune EKF:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-blue-900/20 border border-blue-700 rounded p-4">
        <h3 className="text-sm font-semibold text-blue-300 mb-2">ℹ️ EKF Tuning</h3>
        <p className="text-xs text-blue-200">
          Extended Kalman Filter fuses barometer + IMERG + NWP data. Adjust
          sensitivity and noise parameters to match local conditions.
        </p>
      </div>

      {/* Pressure Sensitivity Slider */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Pressure Sensitivity
          <span className="text-gray-400 font-normal">
            {' '}
            (mm/h per hPa/min)
          </span>
        </label>
        <div className="space-y-2">
          <input
            type="range"
            min="0.05"
            max="0.3"
            step="0.01"
            value={pressureSensitivity}
            onChange={(e) => setPressureSensitivity(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded cursor-pointer"
            aria-label="Barometer pressure sensitivity (Overeem et al. 2019 model)"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>Low sensitivity</span>
            <span className="font-mono font-semibold text-white">
              {pressureSensitivity.toFixed(3)}
            </span>
            <span>High sensitivity</span>
          </div>
          <p className="text-xs text-gray-500">
            Default: {DEFAULT_PARAMS.pressure_sensitivity.toFixed(3)} (Overeem et al. 2019)
          </p>
        </div>
      </div>

      {/* Process Noise (Q) Slider */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Process Noise (Q)
        </label>
        <div className="space-y-2">
          <input
            type="range"
            min="0.01"
            max="1"
            step="0.05"
            value={processNoise}
            onChange={(e) => setProcessNoise(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded cursor-pointer"
            aria-label="EKF process noise covariance"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>Trust model</span>
            <span className="font-mono font-semibold text-white">
              {processNoise.toFixed(3)}
            </span>
            <span>Trust sensors</span>
          </div>
          <p className="text-xs text-gray-500">
            Higher values trust sensors more; lower trusts the rainfall model.
          </p>
        </div>
      </div>

      {/* Measurement Noise (R) Slider */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Measurement Noise (R)
        </label>
        <div className="space-y-2">
          <input
            type="range"
            min="0.1"
            max="2"
            step="0.1"
            value={measurementNoise}
            onChange={(e) => setMeasurementNoise(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded cursor-pointer"
            aria-label="EKF measurement noise covariance"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>Trust observations</span>
            <span className="font-mono font-semibold text-white">
              {measurementNoise.toFixed(3)}
            </span>
            <span>Ignore noise</span>
          </div>
          <p className="text-xs text-gray-500">
            Higher values assume noisier sensors.
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={tuneMutation.isPending}
          className={clsx(
            'flex-1 px-4 py-2 rounded font-semibold flex items-center justify-center gap-2',
            'transition bg-kenya-green text-white hover:bg-green-700',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          <Save className="w-4 h-4" />
          {tuneMutation.isPending ? 'Saving...' : 'Save Parameters'}
        </button>

        <button
          onClick={handleReset}
          disabled={tuneMutation.isPending}
          className="px-4 py-2 rounded font-semibold border border-gray-700 hover:border-gray-600 text-gray-300 transition flex items-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          Reset
        </button>
      </div>

      {tuneMutation.isSuccess && (
        <div className="bg-kenya-green/10 border border-kenya-green rounded p-3">
          <p className="text-kenya-green text-sm font-semibold">
            ✓ Parameters updated successfully (audit logged)
          </p>
        </div>
      )}

      {tuneMutation.isError && (
        <div className="bg-risk-high/10 border border-risk-high rounded p-3">
          <p className="text-risk-high text-sm font-semibold">
            ✗ Failed to update parameters
          </p>
        </div>
      )}
    </div>
  );
}
