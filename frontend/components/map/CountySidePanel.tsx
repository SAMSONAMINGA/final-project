/**
 * County Side Panel Component
 * Displays risk details, SHAP explanations, time-series trend, and simulation trigger
 * Objective: Support decision-maker interpretation with explainability (SHAP factors)
 */

'use client';

import { useState } from 'react';
import { ChevronDown, Play, TrendingUp } from 'lucide-react';
import { useRiskData } from '@/hooks/useRiskData';
import { useTriggerSimulation } from '@/hooks/useSimulation';
import { RiskNode, RiskLevel } from '@/types/floodguard';
import { RiskBadge, RiskGauge } from '@/components/common/RiskBadge';
import { CardSkeleton, RiskNodeSkeleton } from '@/components/common/Skeleton';
import { RiskTrendChart } from '@/components/charts/RiskTrendChart';
import clsx from 'clsx';

interface CountySidePanelProps {
  countyCode: string | null;
  onSimulationTrigger?: (countyCode: string) => void;
}

export function CountySidePanel({
  countyCode,
  onSimulationTrigger,
}: CountySidePanelProps) {
  const { data: riskData, isLoading } = useRiskData(countyCode);
  const triggerSim = useTriggerSimulation();
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null);

  if (!countyCode) {
    return (
      <div className="w-96 bg-gray-900 border-l border-gray-700 p-6 flex items-center justify-center h-full">
        <p className="text-gray-400 text-center">
          Select a county on the map to view risk details
        </p>
      </div>
    );
  }

  if (isLoading || !riskData) {
    return (
      <div className="w-96 bg-gray-900 border-l border-gray-700 p-6 overflow-y-auto space-y-4">
        <CardSkeleton />
        <CardSkeleton />
        <RiskNodeSkeleton />
        <RiskNodeSkeleton />
      </div>
    );
  }

  const handleSimulation = async () => {
    if (countyCode) {
      try {
        await triggerSim.mutateAsync(countyCode);
        onSimulationTrigger?.(countyCode);
      } catch (error) {
        console.error('Simulation trigger failed:', error);
      }
    }
  };

  return (
    <div className="w-96 bg-gray-900 border-l border-gray-700 h-full overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-6 z-10">
        <h2 className="text-2xl font-bold text-white mb-3">
          {riskData.county_name}
        </h2>

        {/* Risk Badge & Score */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <RiskBadge
              riskLevel={riskData.risk_level}
              size="lg"
              className="flex-1"
            />
            <span className="text-2xl font-bold text-white ml-4">
              {(riskData.county_risk_score * 100).toFixed(1)}%
            </span>
          </div>

          <RiskGauge
            score={riskData.county_risk_score}
            ariaLabel={`${riskData.county_name} risk score`}
          />

          <p className="text-xs text-gray-400">
            Updated {new Date(riskData.valid_time).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Risk Trend Chart */}
      <div className="p-6 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Risk Trend (6h)
        </h3>
        <RiskTrendChart countyCode={countyCode} />
      </div>

      {/* Simulation Button */}
      <div className="p-6 border-b border-gray-700">
        <button
          onClick={handleSimulation}
          disabled={triggerSim.isPending}
          className={clsx(
            'w-full px-4 py-3 rounded font-semibold flex items-center justify-center gap-2',
            'transition bg-savanna-gold text-black hover:bg-savanna-dark',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-savanna-gold',
          )}
          aria-label={`Trigger 3D flood simulation for ${riskData.county_name}`}
        >
          <Play className="w-4 h-4" />
          {triggerSim.isPending ? 'Starting...' : 'Trigger 3D Simulation'}
        </button>
        <p className="text-xs text-gray-400 mt-2 text-center">
          View flood propagation in 3D terrain viewer
        </p>
      </div>

      {/* Risk Nodes */}
      <div className="p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white mb-4">
          Risk Nodes ({riskData.nodes.length})
        </h3>

        {riskData.nodes.length === 0 ? (
          <div className="text-gray-400 text-sm text-center py-8">
            No nodes with significant risk detected
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {riskData.nodes.map((node: RiskNode) => (
              <RiskNodeCard
                key={node.node_id}
                node={node}
                isExpanded={expandedNodeId === node.node_id}
                onToggle={() =>
                  setExpandedNodeId(
                    expandedNodeId === node.node_id ? null : node.node_id,
                  )
                }
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Individual risk node card with expandable SHAP explanations
 */
function RiskNodeCard({
  node,
  isExpanded,
  onToggle,
}: {
  node: RiskNode;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden bg-gray-800/50">
      {/* Node summary */}
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-start justify-between hover:bg-gray-700/30 transition text-left focus:outline-none focus:ring-2 focus:ring-maasai-red"
        aria-expanded={isExpanded ? 'true' : 'false'}
        aria-label={`Node ${node.node_id} with ${((node.risk_score * 100).toFixed(1))}% risk`}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="font-mono text-sm font-semibold text-white">
              {node.node_id}
            </h4>
            <RiskBadge
              riskLevel={getRiskLevel(node.risk_score)}
              size="sm"
              showLabel={false}
            />
          </div>
          <p className="text-xs text-gray-400">
            {node.lat.toFixed(4)}°, {node.lng.toFixed(4)}°
          </p>
        </div>

        <div className="ml-2 text-right">
          <div className="font-bold text-white">
            {(node.risk_score * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-gray-400">
            {node.depth_cm} cm depth
          </div>
          <ChevronDown
            className={clsx(
              'w-4 h-4 mt-2 ml-auto transition',
              isExpanded && 'rotate-180',
            )}
          />
        </div>
      </button>

      {/* Expandable details: SHAP factors & alerts */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-700 space-y-4">
          {/* SHAP Top-3 Factors */}
          <div>
            <h5 className="text-xs font-semibold text-gray-400 uppercase mb-2">
              Top 3 Contributing Factors
            </h5>
            <div className="space-y-2">
              {node.shap_top3.map((factor, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <span className="text-gray-300">{factor.factor}</span>
                  <div className="flex-1 mx-2 h-1 bg-gray-700 rounded">
                    <div
                      className="h-1 bg-maasai-red rounded transition"
                      style={{
                        width: `${Math.abs(factor.contribution) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-gray-400 font-mono">
                    {(factor.contribution * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Alert Messages */}
          <div>
            <h5 className="text-xs font-semibold text-gray-400 uppercase mb-2">
              Alert Messages
            </h5>
            <div className="space-y-2">
              <div className="bg-gray-700/30 p-2 rounded text-xs text-gray-300">
                <span className="font-semibold text-white">EN:</span>{' '}
                {node.alert_message_en}
              </div>
              <div className="bg-gray-700/30 p-2 rounded text-xs text-gray-300">
                <span className="font-semibold text-white">SW:</span>{' '}
                {node.alert_message_sw}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getRiskLevel(score: number): RiskLevel {
  if (score < 0.33) return 'Low';
  if (score < 0.66) return 'Medium';
  if (score < 0.85) return 'High';
  return 'Critical';
}
