import {
  Box,
  Button,
  Center,
  Flex,
  FormControl,
  FormErrorMessage,
  FormHelperText,
  FormLabel,
  Heading,
  Input,
  Text,
  VStack,
} from '@invoke-ai/ui-library';
import { useAppDispatch } from 'app/store/storeHooks';
import { setCredentials } from 'features/auth/store/authSlice';
import { memo, useCallback, useState } from 'react';
import { useSetupMutation } from 'services/api/endpoints/auth';

const validatePasswordStrength = (password: string): { isValid: boolean; message: string } => {
  if (password.length < 8) {
    return { isValid: false, message: 'Password must be at least 8 characters long' };
  }

  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /\d/.test(password);

  if (!hasUpper || !hasLower || !hasDigit) {
    return {
      isValid: false,
      message: 'Password must contain uppercase, lowercase, and numbers',
    };
  }

  return { isValid: true, message: '' };
};

export const AdministratorSetup = memo(() => {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [setup, { isLoading, error }] = useSetupMutation();
  const dispatch = useAppDispatch();

  const passwordValidation = validatePasswordStrength(password);
  const passwordsMatch = password === confirmPassword;

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!passwordValidation.isValid) {
        return;
      }

      if (!passwordsMatch) {
        return;
      }

      try {
        const result = await setup({ email, display_name: displayName, password }).unwrap();
        if (result.success) {
          // Auto-login after setup - need to call login API
          // For now, just redirect to login page
          window.location.href = '/login';
        }
      } catch (err) {
        console.error('Setup failed:', err);
      }
    },
    [email, displayName, password, passwordValidation.isValid, passwordsMatch, setup]
  );

  const errorMessage = error
    ? 'data' in error && typeof error.data === 'object' && error.data && 'detail' in error.data
      ? String(error.data.detail)
      : 'Setup failed. Please try again.'
    : null;

  return (
    <Center w="100dvw" h="100dvh" bg="base.900">
      <Box w="full" maxW="500px" p={8} borderRadius="lg" bg="base.800" boxShadow="dark-lg">
        <form onSubmit={handleSubmit}>
          <VStack spacing={6} align="stretch">
            <VStack spacing={2}>
              <Heading size="lg" textAlign="center">
                Welcome to InvokeAI
              </Heading>
              <Text fontSize="sm" color="base.400" textAlign="center">
                Set up your administrator account to get started
              </Text>
            </VStack>

            <FormControl isRequired>
              <FormLabel>Email</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
                autoComplete="email"
                autoFocus
              />
              <FormHelperText>This will be your username for signing in</FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Display Name</FormLabel>
              <Input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Administrator"
              />
              <FormHelperText>Your name as it will appear in the application</FormHelperText>
            </FormControl>

            <FormControl isRequired isInvalid={password.length > 0 && !passwordValidation.isValid}>
              <FormLabel>Password</FormLabel>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="new-password"
              />
              {password.length > 0 && !passwordValidation.isValid && (
                <FormErrorMessage>{passwordValidation.message}</FormErrorMessage>
              )}
              {password.length === 0 && (
                <FormHelperText>
                  Must be at least 8 characters with uppercase, lowercase, and numbers
                </FormHelperText>
              )}
            </FormControl>

            <FormControl isRequired isInvalid={confirmPassword.length > 0 && !passwordsMatch}>
              <FormLabel>Confirm Password</FormLabel>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm Password"
                autoComplete="new-password"
              />
              {confirmPassword.length > 0 && !passwordsMatch && (
                <FormErrorMessage>Passwords do not match</FormErrorMessage>
              )}
            </FormControl>

            <Button
              type="submit"
              isLoading={isLoading}
              loadingText="Setting up..."
              colorScheme="invokeBlue"
              size="lg"
              w="full"
              isDisabled={!passwordValidation.isValid || !passwordsMatch}
            >
              Create Administrator Account
            </Button>

            {errorMessage && (
              <Flex p={3} borderRadius="md" bg="error.500" color="white" fontSize="sm" justifyContent="center">
                <Text fontWeight="semibold">{errorMessage}</Text>
              </Flex>
            )}
          </VStack>
        </form>
      </Box>
    </Center>
  );
});

AdministratorSetup.displayName = 'AdministratorSetup';
