import React, { type ChangeEventHandler, useState } from 'react';
import { classNames } from '../../helpers/strings';
import PrimaryButton from '../../components/PrimaryButton';
import DeleteButton from '../../components/DeleteButton';
import { InfoBanner } from '../../components/InfoBanner';
import startCase from 'lodash/startCase';
import { Account } from '../../types/account';
import useCreateAccount from './useCreateAccount';
import useDeleteAccount from './useDeleteAccount';

type inputAccountCredentials = {
  index: number;
  clearCreateAccounts: () => void;
  account: Account;
};

const InputAccountCredentials: React.FC<inputAccountCredentials> = ({
  clearCreateAccounts,
  index,
  account,
}) => {
  const { isCreating, errorOnCreate, createAccount } = useCreateAccount();
  const { isDeleting, deleteAccount } = useDeleteAccount();
  const credentials = account.connectedAccount?.credentials || {};
  const [credential, setCredential] = useState(credentials);

  const validateCredentials = JSON.parse(
    JSON.stringify(credential),
    (key, value) => value ?? value
  );

  const handleSubmitForm = (e: any): void => {
    e.preventDefault();

    clearCreateAccounts();
    if (e.nativeEvent.submitter.name === 'delete') {
      deleteAccount({
        name: account.name,
        authType: account.authType,
      });
    } else {
      // We only ever create accounts as the endpoint is
      // idempotent
      createAccount({
        name: account.name,
        authType: account.authType,
        connectedAccount: {
          createdAt: Date.now(),
          credentials: validateCredentials,
        },
      });
    }
  };

  // used to handle the state of the credentials attached
  // to the account
  function handleCredentialChange(e: any): void {
    setCredential({
      ...credential,
      [e.target.name]: e.target.value,
    });
  }

  return (
    <React.Fragment>
      <form onSubmit={handleSubmitForm} className="col-span-3">
        <NameInput
          name={account.authType}
          index={index}
          error={errorOnCreate}
        />
        {account.name !== 'facebook' && (
          <CredentialsInputList
            index={index}
            credentials={credentials}
            error={errorOnCreate}
            type={account.name}
            handleCredentialChange={handleCredentialChange}
          />
        )}
        {account.name === 'facebook' && (
          <InfoBanner message="Please note this will not be functional until Facebook approves the Virtual Labs application" />
        )}
        <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
          <DeleteButton type="submit" loading={isDeleting} />
          <PrimaryButton
            type="submit"
            testId={`existing-account-submit-button-${index}`}
            loading={isCreating}
          >
            {account.connectedAccount?.createdAt !== 0 ? 'Update' : 'Connect'}
          </PrimaryButton>
        </div>
      </form>
    </React.Fragment>
  );
};

type nameInputProps = {
  name: string;
  index: number;
  error: string | undefined;
};

const NameInput: React.FC<nameInputProps> = ({ name, index, error }) => {
  return (
    <>
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
    </>
  );
};

type credentialsInputListProp = {
  credentials: any;
  error: string | undefined;
  type: string;
  handleCredentialChange: ChangeEventHandler;
  index: number;
};

const CredentialsInputList: React.FC<credentialsInputListProp> = ({
  credentials,
  error,
  handleCredentialChange,
  type,
  index,
}) => {
  return (
    <>
      {Object.keys(credentials).map(key => (
        <CredentialsInput
          key={`${key}-${index}`}
          index={index}
          name={key}
          type={type}
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
  type: string;
  error: string | undefined;
  handleCredentialChange: ChangeEventHandler;
  index: number;
  name: string;
};

const CredentialsInput: React.FC<credentialsInputProps> = ({
  name,
  value,
  type,
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
        type={typeof value === 'string' ? 'password' : 'text'}
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
        disabled={type === 'facebook'}
      />
    </div>
  );
};

export default InputAccountCredentials;
