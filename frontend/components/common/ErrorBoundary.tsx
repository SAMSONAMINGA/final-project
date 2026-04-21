/**
 * Error Boundary Component
 * WCAG 2.1 AA accessible error handling & fallback UI
 * Objective: Prevent white-screen crashes; guide users to recovery
 */

import React, { ReactNode, Component } from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error('Error boundary caught:', error);
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div
            className="bg-risk-high/10 border border-risk-high rounded-lg p-6 m-4"
            role="alert"
          >
            <div className="flex items-center gap-3 mb-3">
              <AlertCircle className="w-6 h-6 text-risk-high" />
              <h2 className="text-lg font-semibold text-risk-high">
                Something went wrong
              </h2>
            </div>
            <p className="text-gray-300 mb-4">
              {this.state.error?.message || 'An unexpected error occurred. Please try refreshing the page.'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-risk-high text-white rounded hover:bg-risk-critical transition"
              aria-label="Refresh page to recover from error"
            >
              Refresh Page
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
