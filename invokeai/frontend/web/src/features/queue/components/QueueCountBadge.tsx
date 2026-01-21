import { Badge, Portal } from '@invoke-ai/ui-library';
import { useAppSelector } from 'app/store/storeHooks';
import { selectIsAuthenticated } from 'features/auth/store/authSlice';
import type { RefObject } from 'react';
import { memo, useEffect, useMemo, useState } from 'react';
import { useGetQueueStatusQuery } from 'services/api/endpoints/queue';

type Props = {
  targetRef: RefObject<HTMLDivElement>;
};

export const QueueCountBadge = memo(({ targetRef }: Props) => {
  const [badgePos, setBadgePos] = useState<{ x: string; y: string } | null>(null);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const { queueData } = useGetQueueStatusQuery(undefined, {
    selectFromResult: (res) => ({
      queueData: res.data?.queue,
    }),
  });

  const badgeText = useMemo(() => {
    if (!queueData) {
      return null;
    }

    const totalPending = queueData.pending + queueData.in_progress;

    // Hide badge if there are no pending jobs
    if (totalPending === 0) {
      return null;
    }

    // In multiuser mode (authenticated user), show "X/Y" format where X is user's jobs and Y is total jobs
    if (
      isAuthenticated &&
      queueData.user_pending !== undefined &&
      queueData.user_pending !== null &&
      queueData.user_in_progress !== undefined &&
      queueData.user_in_progress !== null
    ) {
      const userPending = queueData.user_pending + queueData.user_in_progress;
      return `${userPending}/${totalPending}`;
    }

    // In single-user mode or when user counts aren't available, show total count only
    return totalPending.toString();
  }, [queueData, isAuthenticated]);

  useEffect(() => {
    if (!targetRef.current) {
      return;
    }

    const target = targetRef.current;
    const parent = target.parentElement;

    if (!parent) {
      return;
    }

    const cb = () => {
      // If the parent element is not visible, we do not want to show the badge. This can be tricky to reliably
      // determine. The best way I've found is to check the bounding rect of the target and its parent.
      const badgeElRect = target.getBoundingClientRect();
      const parentElRect = parent.getBoundingClientRect();
      if (
        badgeElRect.x === 0 ||
        badgeElRect.y === 0 ||
        badgeElRect.width === 0 ||
        badgeElRect.height === 0 ||
        parentElRect.x === 0 ||
        parentElRect.y === 0 ||
        parentElRect.width === 0 ||
        parentElRect.height === 0
      ) {
        setBadgePos(null);
        return;
      }
      setBadgePos({ x: `${badgeElRect.x - 7}px`, y: `${badgeElRect.y - 5}px` });
    };

    const resizeObserver = new ResizeObserver(cb);
    resizeObserver.observe(parent);
    cb();

    return () => {
      resizeObserver.disconnect();
    };
  }, [targetRef]);

  if (!badgeText) {
    return null;
  }
  if (!badgePos) {
    return null;
  }

  return (
    <Portal>
      <Badge
        pos="absolute"
        insetInlineStart={badgePos.x}
        insetBlockStart={badgePos.y}
        colorScheme="invokeYellow"
        zIndex="docked"
        shadow="dark-lg"
        userSelect="none"
      >
        {badgeText}
      </Badge>
    </Portal>
  );
});

QueueCountBadge.displayName = 'QueueCountBadge';
