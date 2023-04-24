import React, { type ChangeEventHandler } from 'react';
import { classNames } from '../../helpers/strings';
import startCase from 'lodash/startCase';

type inputAccountCredentials = {
  index: number;
  error: string | undefined;
  handleCredentialChange: ChangeEventHandler;
  entity: string;
  credentials: any;
};

const InputAccountCredentials: React.FC<inputAccountCredentials> = ({
  error,
  handleCredentialChange,
  index,
  entity,
  credentials,
}) => (
  <React.Fragment>
    <NameInput name={entity} index={index} error={error} />
    <CredentialsInputList
      index={index}
      credentials={credentials}
      error={error}
      handleCredentialChange={handleCredentialChange}
    />
  </React.Fragment>
);

type nameInputProps = {
  name: string;
  index: number;
  error: string | undefined;
};

const NameInput: React.FC<nameInputProps> = ({ name, index, error }) => {
  return (
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Name
      </label>
      <input
        id={`${index}`}
        name="identifier"
        type="text"
        className={classNames(
          'block w-full shadow-sm sm:text-sm rounded-md',
          (error ?? '').trim() !== ''
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
        )}
        placeholder="Name of Credential"
        data-testid={`account-name-input-${index}`}
        value={name}
        disabled
      />
    </div>
  );
};

type credentialsInputListProp = {
  credentials: any;
  error: string | undefined;
  handleCredentialChange: ChangeEventHandler;
  index: number;
};

const CredentialsInputList: React.FC<credentialsInputListProp> = ({
  credentials,
  error,
  handleCredentialChange,
  index,
}) => {
  return (
    <>
      {Object.keys(credentials).map(key => (
        <CredentialsInput
          key={`${key}-${index}`}
          index={index}
          name={key}
          value={credentials[key]}
          error={error}
          handleCredentialChange={handleCredentialChange}
        />
      ))}
    </>
  );
};

type credentialsInputProps = {
  value: string;
  error: string | undefined;
  handleCredentialChange: ChangeEventHandler;
  index: number;
  name: string;
};

const CredentialsInput: React.FC<credentialsInputProps> = ({
  name,
  value,
  error,
  handleCredentialChange,
  index,
}) => {
  return (
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        {startCase(name)}
      </label>
      <input
        id={`${name}-${index}`}
        name={name}
        type="password"
        className={classNames(
          'block w-full shadow-sm sm:text-sm rounded-md',
          (error ?? '').trim() !== ''
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
        )}
        data-testid={`account-input-${name}-${index}`}
        placeholder={`Enter ${startCase(name)}`}
        onChange={handleCredentialChange}
        value={value}
        required
      />
    </div>
  );
};

export default InputAccountCredentials;
