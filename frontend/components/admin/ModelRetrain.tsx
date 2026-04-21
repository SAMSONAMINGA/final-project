/**
 * Model Retrain Component (Admin only)
 * Trigger GATv2 model retraining with historical data date range
 * Objective: Enable seasonal model adaptation (monthly retraining cycles)
 */

'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ModelRetrainRequest } from '@/types/floodguard';
import { api } from '@/lib/api';
import clsx from 'clsx';
import { Zap } from 'lucide-react';
import { format, subDays } from 'date-fns';

export function ModelRetrain() {
  const now = new Date();
  const thirtyDaysAgo = subDays(now, 30);

  const [startDate, setStartDate] = useState(format(thirtyDaysAgo, 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(now, 'yyyy-MM-dd'));
  const [includeSynthetic, setIncludeSynthetic] = useState(false);

  const retrainMutation = useMutation({
    mutationFn: async (request: ModelRetrainRequest) => {
      return api.triggerModelRetrain(request);
    },
  });

  const handleRetrain = async () => {
    try {
      const result = await retrainMutation.mutateAsync({
        start_date: startDate,
        end_date: endDate,
        include_synthetic_data: includeSynthetic,
      });

      alert(
        `Retrain job queued: ${result.job_id}\nMonitor progress in Celery dashboard.`,
      );
    } catch (error) {
      console.error('Failed to trigger retrain:', error);
      alert('Failed to queue retrain job.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-amber-900/20 border border-amber-700 rounded p-4">
        <h3 className="text-sm font-semibold text-amber-300 mb-2">
          ⏱️ Model Retraining
        </h3>
        <p className="text-xs text-amber-200">
          Retraining GATv2 on historical data improves predictions as patterns
          evolve. Typical runtime: 4-6 hours on GPU cluster.
        </p>
      </div>

      {/* Date Range Selection */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="start-date" className="block text-sm font-semibold text-white mb-2">
            Start Date
          </label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-savanna-gold"
          />
        </div>

        <div>
          <label htmlFor="end-date" className="block text-sm font-semibold text-white mb-2">
            End Date
          </label>
          <input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-savanna-gold"
          />
        </div>
      </div>

      {/* Synthetic Data Toggle */}
      <div className="flex items-center gap-3">
        <input
          id="synthetic"
          type="checkbox"
          checked={includeSynthetic}
          onChange={(e) => setIncludeSynthetic(e.target.checked)}
          className="w-4 h-4 rounded bg-gray-700 border border-gray-600 cursor-pointer"
        />
        <label htmlFor="synthetic" className="text-sm text-gray-300 cursor-pointer">
          Include synthetic gauge data (improved coverage in rural areas)
        </label>
      </div>

      {/* Queue Retrain Button */}
      <button
        onClick={handleRetrain}
        disabled={retrainMutation.isPending}
        className={clsx(
          'w-full px-4 py-3 rounded font-semibold flex items-center justify-center gap-2',
          'transition bg-amber-600 text-white hover:bg-amber-700',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-600',
        )}
      >
        <Zap className="w-4 h-4" />
        {retrainMutation.isPending
          ? 'Queueing...'
          : 'Queue Retrain Job (4-6h runtime)'}
      </button>

      {retrainMutation.isSuccess && (
        <div className="bg-kenya-green/10 border border-kenya-green rounded p-4 space-y-2">
          <p className="text-kenya-green text-sm font-semibold">
            ✓ Retrain job queued successfully
          </p>
          <p className="text-xs text-gray-400">
            Check Celery dashboard for progress updates.
          </p>
        </div>
      )}

      {retrainMutation.isError && (
        <div className="bg-risk-high/10 border border-risk-high rounded p-4">
          <p className="text-risk-high text-sm font-semibold">
            ✗ Failed to queue retrain job
          </p>
        </div>
      )}
    </div>
  );
}
