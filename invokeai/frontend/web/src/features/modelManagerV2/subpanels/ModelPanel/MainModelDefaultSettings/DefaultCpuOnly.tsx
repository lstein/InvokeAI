import { Flex, FormControl, FormLabel, Switch } from '@invoke-ai/ui-library';
import { InformationalPopover } from 'common/components/InformationalPopover/InformationalPopover';
import { SettingToggle } from 'features/modelManagerV2/subpanels/ModelPanel/SettingToggle';
import { memo, useCallback, useMemo } from 'react';
import type { ChangeEvent } from 'react';
import type { UseControllerProps } from 'react-hook-form';
import { useController } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

import type { MainModelDefaultSettingsFormData } from './MainModelDefaultSettings';

type DefaultCpuOnly = MainModelDefaultSettingsFormData['cpuOnly'];

export const DefaultCpuOnly = memo((props: UseControllerProps<MainModelDefaultSettingsFormData>) => {
  const { field } = useController(props);

  const { t } = useTranslation();

  const onChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const updatedValue = {
        ...(field.value as DefaultCpuOnly),
        value: e.target.checked,
      };
      field.onChange(updatedValue);
    },
    [field]
  );

  const value = useMemo(() => {
    return (field.value as DefaultCpuOnly).value;
  }, [field.value]);

  const isDisabled = useMemo(() => {
    return !(field.value as DefaultCpuOnly).isEnabled;
  }, [field.value]);

  return (
    <FormControl flexDir="column" gap={2} alignItems="flex-start">
      <Flex justifyContent="space-between" w="full">
        <InformationalPopover feature="cpuOnly">
          <FormLabel>{t('modelManager.cpuOnly')}</FormLabel>
        </InformationalPopover>
        <SettingToggle control={props.control} name="cpuOnly" />
      </Flex>

      <Switch isChecked={value} onChange={onChange} isDisabled={isDisabled}>
        {t('modelManager.runOnCpu')}
      </Switch>
    </FormControl>
  );
});

DefaultCpuOnly.displayName = 'DefaultCpuOnly';
