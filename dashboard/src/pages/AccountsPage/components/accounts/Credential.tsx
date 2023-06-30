import { ChangeEventHandler } from 'react';
import { classNames, createLabelFor } from '../../../../helpers/strings';

type CredentialProps = {
  index: number;
  name: string;
  value: string;
  authType: string;
  error: string | undefined;
  handleChange: ChangeEventHandler;
  isDirty: boolean;
};

const Credential: React.FC<CredentialProps> = ({
  index,
  name,
  value,
  authType,
  error,
  handleChange,
  isDirty,
}) => {
  return (
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        {createLabelFor(name)}
      </label>
      <input
        id={`${name}-${index}`}
        name={name}
        type={typeof value === 'string' ? 'password' : 'text'}
        className={classNames(
          'block w-full shadow-sm sm:text-sm rounded-md',
          (error ?? '').trim() !== ''
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
        )}
        data-testid={`account-input-${name}-${index}`}
        placeholder={value ? value : `Enter your ${name.replace(/_/g, ' ')}`}
        onChange={handleChange}
        value={value}
        required={isDirty ? true : false}
        disabled={authType === 'facebook'}
      />
    </div>
  );
};

export default Credential;
