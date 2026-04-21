/**
 * Alerts Page — SMS/USSD Message Dispatch
 * Form to send alerts with multilingual preview and delivery tracking
 */

'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { AlertComposer } from '@/components/alerts/AlertComposer';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function AlertsPage() {
  const selectedCountyCode = useAppStore((s) => s.selectedCountyCode);
  const [targetCounty, setTargetCounty] = useState(selectedCountyCode || 'KEN01');

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
          <h1 className="text-3xl font-bold text-white">Alert Dispatch</h1>
          <p className="text-gray-400 mt-2">
            Send SMS/USSD warnings to volunteer coordinators and residents
          </p>
        </div>

        {/* Content */}
        <div className="max-w-4xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* County Selection */}
          <div className="lg:col-span-2">
            <label htmlFor="county" className="block text-sm font-semibold text-white mb-3">
              Target County
            </label>
            <select
              id="county"
              value={targetCounty}
              onChange={(e) => setTargetCounty(e.target.value)}
              className="w-full px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-savanna-gold"
            >
              {[
                'KEN01-Mombasa',
                'KEN02-Kwale',
                'KEN03-Kilifi',
                'KEN04-TanaRiver',
              ].map((county) => (
                <option key={county} value={county.split('-')[0]}>
                  {county}
                </option>
              ))}
            </select>
          </div>

          {/* Alert Composer */}
          <div className="lg:col-span-2 card">
            <h2 className="text-lg font-semibold text-white mb-4">
              Message Composer
            </h2>
            <AlertComposer countyCode={targetCounty} />
          </div>

          {/* Delivery Tracking (Demo) */}
          <div className="lg:col-span-2 card">
            <h2 className="text-lg font-semibold text-white mb-4">
              Recent Deliveries
            </h2>
            <div className="space-y-3">
              {[
                { id: 'ALT001', status: 'delivered', recipients: 45, time: '2 hours ago' },
                { id: 'ALT002', status: 'sent', recipients: 32, time: '5 hours ago' },
              ].map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-4 bg-gray-700/30 rounded"
                >
                  <div>
                    <p className="font-mono font-semibold text-white">{alert.id}</p>
                    <p className="text-xs text-gray-400">
                      {alert.recipients} recipients • {alert.time}
                    </p>
                  </div>
                  <span
                    className={clsx(
                      'px-3 py-1 rounded text-xs font-semibold',
                      alert.status === 'delivered'
                        ? 'bg-kenya-green/20 text-kenya-green'
                        : 'bg-amber-500/20 text-amber-400',
                    )}
                  >
                    {alert.status === 'delivered' ? '✓ Delivered' : '→ Sent'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}

import clsx from 'clsx';
