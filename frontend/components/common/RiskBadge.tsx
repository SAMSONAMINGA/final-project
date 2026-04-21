/**
 * Risk Level Badge Component
 * WCAG 2.1 AA accessible colour-coded risk indication
 * Color palette: Kenyan savanna theme (green/yellow/orange/red)
 */

import clsx from 'clsx';
import { RiskLevel } from '@/types/floodguard';

interface RiskBadgeProps {
  riskLevel: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

// Accessible colour mappings with WCAG AA contrast ratios
const riskColours: Record<RiskLevel, { bg: string; text: string; icon: string }> = {
  Low: { bg: 'bg-risk-low', text: 'text-white', icon: '✓' },
  Medium: { bg: 'bg-risk-medium', text: 'text-white', icon: '!' },
  High: { bg: 'bg-risk-high', text: 'text-white', icon: '⚠' },
  Critical: { bg: 'bg-risk-critical', text: 'text-white', icon: '🚨' },
};

const sizeClasses = {
  sm: 'px-2 py-1 text-xs',
  md: 'px-3 py-1.5 text-sm',
  lg: 'px-4 py-2 text-base',
};

export function RiskBadge({
  riskLevel,
  size = 'md',
  showLabel = true,
  className,
}: RiskBadgeProps) {
  const colour = riskColours[riskLevel];

  return (
    <div
      className={clsx(
        'inline-flex items-center gap-2 rounded font-semibold',
        colour.bg,
        colour.text,
        sizeClasses[size],
        className,
      )}
      role="img"
      aria-label={`Risk level: ${riskLevel}`}
    >
      <span>{colour.icon}</span>
      {showLabel && <span>{riskLevel}</span>}
    </div>
  );
}

/**
 * Risk Score Gauge Component
 * Visual 0-100 scale with accessible aria-valuenow
 */
export function RiskGauge({
  score,
  label,
  ariaLabel,
}: {
  score: number;
  label?: string;
  ariaLabel?: string;
}) {
  const normalized = Math.min(100, Math.max(0, score * 100));
  const colour =
    normalized < 25
      ? 'bg-risk-low'
      : normalized < 50
      ? 'bg-risk-medium'
      : normalized < 75
      ? 'bg-risk-high'
      : 'bg-risk-critical';

  return (
    <div className="w-full">
      {label && <p className="text-sm font-medium text-gray-300 mb-2">{label}</p>}
      <div
        className="w-full h-2 bg-gray-700 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={normalized}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={ariaLabel || 'Risk score gauge'}
      >
        <div
          className={clsx('h-full transition-all', colour)}
          style={{ width: `${normalized}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">
        {normalized.toFixed(1)}%
      </p>
    </div>
  );
}
