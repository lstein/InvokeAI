import { Center, Spinner } from '@invoke-ai/ui-library';
import { useAppSelector } from 'app/store/storeHooks';
import type { RootState } from 'app/store/store';
import type { PropsWithChildren } from 'react';
import { memo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface ProtectedRouteProps {
  requireAdmin?: boolean;
}

export const ProtectedRoute = memo(({ children, requireAdmin = false }: PropsWithChildren<ProtectedRouteProps>) => {
  const isAuthenticated = useAppSelector((state: RootState) => state.auth?.isAuthenticated || false);
  const isLoading = useAppSelector((state: RootState) => state.auth?.isLoading || false);
  const user = useAppSelector((state: RootState) => state.auth?.user);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login', { replace: true });
    } else if (!isLoading && isAuthenticated && requireAdmin && !user?.is_admin) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, isLoading, requireAdmin, user?.is_admin, navigate]);

  if (isLoading) {
    return (
      <Center w="100dvw" h="100dvh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requireAdmin && !user?.is_admin) {
    return null;
  }

  return <>{children}</>;
});

ProtectedRoute.displayName = 'ProtectedRoute';
