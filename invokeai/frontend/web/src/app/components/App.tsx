import { Box } from '@invoke-ai/ui-library';
import { useStore } from '@nanostores/react';
import { GlobalHookIsolator } from 'app/components/GlobalHookIsolator';
import { GlobalModalIsolator } from 'app/components/GlobalModalIsolator';
import { clearStorage } from 'app/store/enhancers/reduxRemember/driver';
import Loading from 'common/components/Loading/Loading';
import { AdministratorSetup } from 'features/auth/components/AdministratorSetup';
import { LoginPage } from 'features/auth/components/LoginPage';
import { ProtectedRoute } from 'features/auth/components/ProtectedRoute';
import { AppContent } from 'features/ui/components/AppContent';
import { navigationApi } from 'features/ui/layouts/navigation-api';
import { memo } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { Route, Routes } from 'react-router-dom';

import AppErrorBoundaryFallback from './AppErrorBoundaryFallback';
import ThemeLocaleProvider from './ThemeLocaleProvider';

const errorBoundaryOnReset = () => {
  clearStorage();
  location.reload();
  return false;
};

const MainApp = () => {
  const isNavigationAPIConnected = useStore(navigationApi.$isConnected);
  return (
    <Box id="invoke-app-wrapper" w="100dvw" h="100dvh" position="relative" overflow="hidden">
      {isNavigationAPIConnected ? <AppContent /> : <Loading />}
    </Box>
  );
};

const App = () => {
  return (
    <ThemeLocaleProvider>
      <ErrorBoundary onReset={errorBoundaryOnReset} FallbackComponent={AppErrorBoundaryFallback}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/setup" element={<AdministratorSetup />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <MainApp />
              </ProtectedRoute>
            }
          />
        </Routes>
        <GlobalHookIsolator />
        <GlobalModalIsolator />
      </ErrorBoundary>
    </ThemeLocaleProvider>
  );
};

export default memo(App);
