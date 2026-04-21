/**
 * Loading Skeleton Component
 * WCAG 2.1 AA accessible loading states for async data
 * Objective: Improve perceived performance and UX during data fetching
 */

import clsx from 'clsx';

interface SkeletonProps {
  width?: string;
  height?: string;
  className?: string;
  count?: number;
}

export function Skeleton({
  width = 'w-full',
  height = 'h-4',
  className,
  count = 1,
}: SkeletonProps) {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <div className={clsx('space-y-2', className)}>
      {items.map((i) => (
        <div
          key={i}
          className={clsx(
            width,
            height,
            'bg-gray-700 rounded animate-pulse',
            'aria-label="Loading..."',
          )}
          role="status"
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="border border-gray-700 rounded-lg p-4 space-y-4 bg-gray-900">
      <Skeleton height="h-8" width="w-3/4" />
      <div className="space-y-2">
        <Skeleton height="h-4" />
        <Skeleton height="h-4" width="w-5/6" />
        <Skeleton height="h-4" width="w-4/6" />
      </div>
    </div>
  );
}

export function RiskNodeSkeleton() {
  return (
    <div className="border-l-4 border-gray-700 pl-4 py-2 space-y-2">
      <Skeleton height="h-5" width="w-1/3" />
      <Skeleton height="h-4" width="w-1/2" />
      <Skeleton height="h-4" width="w-2/3" />
    </div>
  );
}
