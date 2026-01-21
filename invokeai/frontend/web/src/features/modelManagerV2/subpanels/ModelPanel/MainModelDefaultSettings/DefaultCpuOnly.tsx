import { FormControl, FormLabel, Switch } from '@invoke-ai/ui-library';
import { InformationalPopover } from 'common/components/InformationalPopover/InformationalPopover';
import type { ChangeEvent } from 'react';
import { memo, useCallback, useMemo } from 'react';
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
        isEnabled: e.target.checked,
      };
      field.onChange(updatedValue);
    },
    [field]
  );

  const value = useMemo(() => {
    return (field.value as DefaultCpuOnly).value;
  }, [field.value]);

  return (
    <FormControl>
      <InformationalPopover feature="cpuOnly">
        <FormLabel>{t('modelManager.runOnCpu')}</FormLabel>
      </InformationalPopover>
      <Switch isChecked={value} onChange={onChange} />
    </FormControl>
  );
});

DefaultCpuOnly.displayName = 'DefaultCpuOnly';
