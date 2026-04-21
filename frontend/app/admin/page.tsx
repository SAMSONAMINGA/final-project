/**
 * Admin Dashboard Page (Protected)
 * EKF parameter tuning, model retraining, volunteer device registry, audit logs
 * Objective: Enable operational control & accountability (audit logging)
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { EKFTuner } from '@/components/admin/EKFTuner';
import { ModelRetrain } from '@/components/admin/ModelRetrain';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ArrowLeft, Zap, BarChart3, Users, FileText } from 'lucide-react';
import Link from 'next/link';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<'ekf' | 'retrain' | 'volunteers' | 'audit'>('ekf');
  const [selectedCounty, setSelectedCounty] = useState('KEN01');

  const { data: auditLogs, isLoading: auditLoading } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => api.getAuditLogs(1, 20),
  });

  const { data: volunteers, isLoading: volunteersLoading } = useQuery({
    queryKey: ['volunteers'],
    queryFn: () => api.getVolunteerDevices(),
  });

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-900">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-savanna-gold hover:text-savanna-dark transition mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-white">Admin Dashboard</h1>
          <p className="text-gray-400 mt-2">
            Model tuning, retraining, device management, and audit logs
          </p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-700 px-6">
          <div className="flex gap-8">
            {[
              { id: 'ekf', label: 'EKF Tuning', icon: Zap },
              { id: 'retrain', label: 'Model Retrain', icon: BarChart3 },
              { id: 'volunteers', label: 'Devices', icon: Users },
              { id: 'audit', label: 'Audit Logs', icon: FileText },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={clsx(
                  'px-4 py-4 font-semibold flex items-center gap-2 border-b-2 transition',
                  activeTab === id
                    ? 'border-savanna-gold text-white'
                    : 'border-transparent text-gray-400 hover:text-gray-300',
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* EKF Tuning Tab */}
          {activeTab === 'ekf' && (
            <div className="space-y-6">
              <div>
                <label htmlFor="county-select" className="block text-sm font-semibold text-white mb-3">
                  Select County
                </label>
                <select
                  id="county-select"
                  value={selectedCounty}
                  onChange={(e) => setSelectedCounty(e.target.value)}
                  className="w-full px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-savanna-gold"
                >
                  {['KEN01', 'KEN02', 'KEN03', 'KEN04'].map((code) => (
                    <option key={code} value={code}>
                      {code}
                    </option>
                  ))}
                </select>
              </div>
              <EKFTuner countyCode={selectedCounty} />
            </div>
          )}

          {/* Model Retrain Tab */}
          {activeTab === 'retrain' && <ModelRetrain />}

          {/* Volunteers Tab */}
          {activeTab === 'volunteers' && (
            <div className="space-y-6">
              <div className="card">
                <h2 className="text-lg font-semibold text-white mb-4">
                  Registered Barometer Devices ({volunteers?.length || 0})
                </h2>
                {volunteersLoading ? (
                  <p className="text-gray-400">Loading...</p>
                ) : volunteers && volunteers.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-gray-700">
                        <tr>
                          <th className="text-left px-4 py-2 text-gray-400">Device ID (hash)</th>
                          <th className="text-left px-4 py-2 text-gray-400">County</th>
                          <th className="text-right px-4 py-2 text-gray-400">Readings</th>
                          <th className="text-left px-4 py-2 text-gray-400">Last Reading</th>
                        </tr>
                      </thead>
                      <tbody>
                        {volunteers.map((device) => (
                          <tr
                            key={device.device_id_hash}
                            className="border-b border-gray-700 hover:bg-gray-800/30"
                          >
                            <td className="px-4 py-3 font-mono text-xs text-gray-300">
                              {device.device_id_hash.slice(0, 16)}...
                            </td>
                            <td className="px-4 py-3 text-gray-300">{device.county_code}</td>
                            <td className="px-4 py-3 text-right text-gray-300">
                              {device.reading_count}
                            </td>
                            <td className="px-4 py-3 text-gray-400">
                              {device.last_reading_at
                                ? new Date(device.last_reading_at).toLocaleDateString()
                                : 'Never'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-400">No devices registered</p>
                )}
              </div>
            </div>
          )}

          {/* Audit Logs Tab */}
          {activeTab === 'audit' && (
            <div className="card">
              <h2 className="text-lg font-semibold text-white mb-4">
                Audit Log ({auditLogs?.total || 0} entries)
              </h2>
              {auditLoading ? (
                <p className="text-gray-400">Loading...</p>
              ) : auditLogs && auditLogs.items.length > 0 ? (
                <div className="space-y-3">
                  {auditLogs.items.map((entry) => (
                    <div
                      key={entry.id}
                      className="border border-gray-700 rounded p-4 bg-gray-800/30"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-semibold text-white">
                            {entry.event_type}
                          </p>
                          <p className="text-xs text-gray-400">
                            by {entry.user_id} •{' '}
                            {new Date(entry.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      {entry.new_values && (
                        <p className="text-xs text-gray-300">
                          Changes: {JSON.stringify(entry.new_values)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400">No audit logs</p>
              )}
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

import clsx from 'clsx';
