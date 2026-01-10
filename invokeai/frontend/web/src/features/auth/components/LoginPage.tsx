import {
  Box,
  Button,
  Center,
  Checkbox,
  Flex,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  Input,
  Text,
  VStack,
} from '@invoke-ai/ui-library';
import { useAppDispatch } from 'app/store/storeHooks';
import { setCredentials } from 'features/auth/store/authSlice';
import { memo, useCallback, useState } from 'react';
import { useLoginMutation } from 'services/api/endpoints/auth';

export const LoginPage = memo(() => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [login, { isLoading, error }] = useLoginMutation();
  const dispatch = useAppDispatch();

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        const result = await login({ email, password, remember_me: rememberMe }).unwrap();
        // Map the UserDTO from API to our User type
        const user = {
          user_id: result.user.user_id,
          email: result.user.email,
          display_name: result.user.display_name || null,
          is_admin: result.user.is_admin || false,
          is_active: result.user.is_active || true,
        };
        dispatch(setCredentials({ token: result.token, user }));
      } catch (err) {
        // Error is handled by RTK Query and displayed via error state
        console.error('Login failed:', err);
      }
    },
    [email, password, rememberMe, login, dispatch]
  );

  const errorMessage = error ? ('data' in error && typeof error.data === 'object' && error.data && 'detail' in error.data ? String(error.data.detail) : 'Login failed. Please check your credentials.') : null;

  return (
    <Center w="100dvw" h="100dvh" bg="base.900">
      <Box
        w="full"
        maxW="400px"
        p={8}
        borderRadius="lg"
        bg="base.800"
        boxShadow="dark-lg"
      >
        <form onSubmit={handleSubmit}>
          <VStack spacing={6} align="stretch">
            <Heading size="lg" textAlign="center">
              Sign In to InvokeAI
            </Heading>

            <FormControl isRequired isInvalid={!!errorMessage}>
              <FormLabel>Email</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                autoComplete="email"
                autoFocus
              />
            </FormControl>

            <FormControl isRequired isInvalid={!!errorMessage}>
              <FormLabel>Password</FormLabel>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
              />
              {errorMessage && (
                <FormErrorMessage>{errorMessage}</FormErrorMessage>
              )}
            </FormControl>

            <Checkbox
              isChecked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            >
              Remember me for 7 days
            </Checkbox>

            <Button
              type="submit"
              isLoading={isLoading}
              loadingText="Signing in..."
              colorScheme="invokeBlue"
              size="lg"
              w="full"
            >
              Sign In
            </Button>

            {errorMessage && (
              <Flex
                p={3}
                borderRadius="md"
                bg="error.500"
                color="white"
                fontSize="sm"
                justifyContent="center"
              >
                <Text fontWeight="semibold">{errorMessage}</Text>
              </Flex>
            )}
          </VStack>
        </form>
      </Box>
    </Center>
  );
});

LoginPage.displayName = 'LoginPage';
