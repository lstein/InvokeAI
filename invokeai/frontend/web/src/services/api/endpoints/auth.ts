import type { components } from 'services/api/schema';
import { api } from 'services/api';

type LoginRequest = {
  email: string;
  password: string;
  remember_me?: boolean;
};

type LoginResponse = {
  token: string;
  user: components['schemas']['UserDTO'];
  expires_in: number;
};

type SetupRequest = {
  email: string;
  display_name: string;
  password: string;
};

type SetupResponse = {
  success: boolean;
  user: components['schemas']['UserDTO'];
};

type MeResponse = components['schemas']['UserDTO'];

type LogoutResponse = {
  success: boolean;
};

export const authApi = api.injectEndpoints({
  endpoints: (build) => ({
    login: build.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: 'api/v1/auth/login',
        method: 'POST',
        body: credentials,
      }),
    }),
    logout: build.mutation<LogoutResponse, void>({
      query: () => ({
        url: 'api/v1/auth/logout',
        method: 'POST',
      }),
    }),
    getCurrentUser: build.query<MeResponse, void>({
      query: () => 'api/v1/auth/me',
    }),
    setup: build.mutation<SetupResponse, SetupRequest>({
      query: (setupData) => ({
        url: 'api/v1/auth/setup',
        method: 'POST',
        body: setupData,
      }),
    }),
  }),
});

export const { useLoginMutation, useLogoutMutation, useGetCurrentUserQuery, useSetupMutation } = authApi;
