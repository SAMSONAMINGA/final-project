/**
 * Alert Composer Component
 * Multi-language alert message preview & dispatch interface
 * Objective: >90% SMS reach via Africa's Talking with message preview
 */

'use client';

import { useState, type ChangeEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AlertDispatchRequest } from '@/types/floodguard';
import { api } from '@/lib/api';
import { RiskBadge } from '@/components/common/RiskBadge';
import clsx from 'clsx';
import { Send } from 'lucide-react';

interface AlertComposerProps {
  countyCode: string;
}

type AlertLanguage = 'en' | 'sw' | 'sheng';
type AlertRiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';

const SAMPLE_MESSAGES: Record<AlertLanguage, Record<AlertRiskLevel, string>> = {
  en: {
    Low: 'Flood risk is LOW. No immediate action needed.',
    Medium:
      'ALERT: Flood risk is MEDIUM in your area. Prepare evacuation plan.',
    High: 'WARNING: Flood risk is HIGH. Evacuate immediately to higher ground.',
    Critical:
      'CRITICAL: Severe flooding imminent! Evacuate NOW to highest available ground!',
  },
  sw: {
    Low: 'Hatari ya mabingu ni NDOGO. Hakuna hatari maalum.',
    Medium: 'ONYO: Hatari ya mabingu ni KATIKATI. Jiandae kuondoka.',
    High: 'AGIZO: Hatari ya mabingu ni KUBWA. Ondoka sasa hivi!',
    Critical: 'HATARI KUBWA: Mabingu makubwa yanakuja! Ondoka sasa!',
  },
  sheng: {
    Low: 'Risk iko LOW. Hakuna lazima ya kusogea sasa.',
    Medium: 'ONYO: Risk iko MEDIUM. Jipe muda uwe tayari.',
    High: 'WARNING: Risk iko HIGH. Ondoka kwenda juu sasa.',
    Critical: 'HATARI: Flood kali inakuja! Ondoka sasa hivi kwa juu!',
  },
};

export function AlertComposer({ countyCode }: AlertComposerProps) {
  const [phoneNumbers, setPhoneNumbers] = useState('');
  const [language, setLanguage] = useState<AlertLanguage>('en');
  const [messageType, setMessageType] = useState<'sms' | 'ussd'>('sms');
  const [riskLevel, setRiskLevel] = useState<AlertRiskLevel>('Medium');

  const sendAlert = useMutation({
    mutationFn: async (request: AlertDispatchRequest) => {
      return api.sendAlert(request);
    },
  });

  const phones = phoneNumbers
    .split('\n')
    .map((p: string) => p.trim())
    .filter((p: string) => p.length > 0);

  const previewMessage: string = SAMPLE_MESSAGES[language][riskLevel];

  const handleSendAlert = async () => {
    if (phones.length === 0) {
      alert('Please enter at least one phone number');
      return;
    }

    try {
      await sendAlert.mutateAsync({
        county_code: countyCode,
        risk_level: riskLevel,
        phone_numbers: phones,
        message_type: messageType,
        language,
      });

      alert(`Alert sent to ${phones.length} recipient(s)`);
      setPhoneNumbers('');
    } catch (error) {
      console.error('Failed to send alert:', error);
      alert('Failed to send alert. Please try again.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Risk Level Selection */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Risk Level
        </label>
        <div className="grid grid-cols-4 gap-2">
          {(['Low', 'Medium', 'High', 'Critical'] as AlertRiskLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => setRiskLevel(level)}
              aria-label={`Select ${level} risk level`}
              title={`Select ${level} risk level`}
              className={clsx(
                'px-3 py-2 rounded font-semibold text-sm transition',
                riskLevel === level
                  ? 'ring-2 ring-savanna-gold'
                  : 'border border-gray-700 hover:border-gray-600',
              )}
            >
              <RiskBadge riskLevel={level} size="sm" showLabel={true} />
            </button>
          ))}
        </div>
      </div>

      {/* Language Selection */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Language
        </label>
        <div className="flex gap-2">
          {(['en', 'sw', 'sheng'] as AlertLanguage[]).map((lang) => (
            <button
              key={lang}
              onClick={() => setLanguage(lang)}
              aria-label={`Select ${lang === 'en' ? 'English' : lang === 'sw' ? 'Swahili' : 'Sheng'}`}
              title={`Select ${lang === 'en' ? 'English' : lang === 'sw' ? 'Swahili' : 'Sheng'}`}
              className={clsx(
                'px-4 py-2 rounded font-semibold text-sm transition',
                language === lang
                  ? 'bg-savanna-gold text-black'
                  : 'border border-gray-700 hover:border-gray-600',
              )}
            >
              {lang === 'en' ? 'English' : lang === 'sw' ? 'Swahili' : 'Sheng'}
            </button>
          ))}
        </div>
      </div>

      {/* Message Type */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Message Type
        </label>
        <div className="flex gap-2">
          {(['sms', 'ussd'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setMessageType(type)}
              className={clsx(
                'flex-1 px-4 py-2 rounded font-semibold text-sm transition',
                messageType === type
                  ? 'bg-maasai-red text-white'
                  : 'border border-gray-700 hover:border-gray-600',
              )}
            >
              {type === 'sms' ? 'SMS' : 'USSD'}
            </button>
          ))}
        </div>
      </div>

      {/* Message Preview */}
      <div>
        <label className="block text-sm font-semibold text-white mb-3">
          Message Preview
        </label>
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <p className="text-gray-300 text-sm leading-relaxed">
            {previewMessage}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            {previewMessage.length > 160 ? 'Multi-part SMS' : 'Single SMS'} (
            {previewMessage.length} chars)
          </p>
        </div>
      </div>

      {/* Phone Numbers Input */}
      <div>
        <label htmlFor="phones" className="block text-sm font-semibold text-white mb-3">
          Phone Numbers (E.164 format, one per line)
        </label>
        <textarea
          id="phones"
          value={phoneNumbers}
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setPhoneNumbers(e.target.value)}
          placeholder="+254712345678&#10;+254787654321"
          className="w-full px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-savanna-gold"
          rows={6}
        />
        <p className="text-xs text-gray-400 mt-2">
          {phones.length} recipient{phones.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Send Button */}
      <button
        onClick={handleSendAlert}
        disabled={sendAlert.isPending || phones.length === 0}
        className={clsx(
          'w-full px-4 py-3 rounded font-semibold flex items-center justify-center gap-2',
          'transition bg-kenya-green text-white hover:bg-green-700',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-kenya-green',
        )}
        aria-label={`Send alert to ${phones.length} recipient${phones.length !== 1 ? 's' : ''}`}
      >
        <Send className="w-4 h-4" />
        {sendAlert.isPending ? 'Sending...' : `Send to ${phones.length}`}
      </button>

      {sendAlert.isSuccess && (
        <div className="bg-kenya-green/10 border border-kenya-green rounded p-4">
          <p className="text-kenya-green text-sm font-semibold">
            ✓ Alert sent successfully
          </p>
        </div>
      )}

      {sendAlert.isError && (
        <div className="bg-risk-high/10 border border-risk-high rounded p-4">
          <p className="text-risk-high text-sm font-semibold">
            ✗ Failed to send alert
          </p>
        </div>
      )}
    </div>
  );
}
