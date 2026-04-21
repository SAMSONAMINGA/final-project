/**
 * Risk Trend Chart Component
 * Recharts-based time-series visualization of county risk over last 6 hours
 * Objective: Enable temporal pattern recognition for decision makers
 */

'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { format, subHours } from 'date-fns';

interface RiskTrendChartProps {
  countyCode: string;
}

/**
 * Generate synthetic 6h trend data for demonstration
 * In production, this would fetch from /risk/{county_code}/history endpoint
 */
function generateTrendData() {
  const now = new Date();
  const data = [];

  for (let i = 6; i >= 0; i--) {
    const timestamp = subHours(now, i);
    // Simulate realistic risk progression with noise
    const baseRisk = 0.3 + Math.sin(i / 3.5) * 0.2;
    const noise = (Math.random() - 0.5) * 0.1;
    const risk = Math.max(0, Math.min(1, baseRisk + noise));

    data.push({
      timestamp: format(timestamp, 'HH:mm'),
      risk: parseFloat((risk * 100).toFixed(1)),
      iso: timestamp.toISOString(),
    });
  }

  return data;
}

export function RiskTrendChart({ countyCode }: RiskTrendChartProps) {
  const data = useMemo(() => generateTrendData(), []);

  const currentRisk = data[data.length - 1]?.risk || 0;
  const previousRisk = data[data.length - 2]?.risk || 0;
  const trend = currentRisk > previousRisk ? 'up' : 'down';

  return (
    <div className="space-y-3">
      {/* Current risk indicator */}
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-white">
          {currentRisk.toFixed(1)}%
        </span>
        <span
          className={clsx(
            'text-xs font-semibold',
            trend === 'up' ? 'text-risk-high' : 'text-risk-low',
          )}
        >
          {trend === 'up' ? '↑' : '↓'}{' '}
          {Math.abs(currentRisk - previousRisk).toFixed(1)}%
        </span>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#374151"
            vertical={false}
          />
          <XAxis
            dataKey="timestamp"
            stroke="#9CA3AF"
            style={{ fontSize: '12px' }}
            interval={Math.floor(data.length / 3)}
          />
          <YAxis
            stroke="#9CA3AF"
            style={{ fontSize: '12px' }}
            domain={[0, 100]}
            label={{ value: '%', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '0.5rem',
            }}
            labelStyle={{ color: '#F3F4F6' }}
            formatter={(value: number) => `${value.toFixed(1)}%`}
            cursor={{ stroke: '#D4AF37', strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="risk"
            stroke="#D4AF37"
            strokeWidth={3}
            dot={false}
            isAnimationActive={true}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Interpretation */}
      <p className="text-xs text-gray-400">
        {trend === 'up'
          ? 'Risk is increasing. Monitor closely.'
          : 'Risk is stabilizing. Good sign.'}
      </p>
    </div>
  );
}

import clsx from 'clsx';
