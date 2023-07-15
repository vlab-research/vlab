import React, { useEffect, useState } from 'react';
import PrimaryButton from '../../../../components/PrimaryButton';
import DeleteButton from '../../../../components/DeleteButton';
import { InfoBanner } from '../../../../components/InfoBanner';
import Credential from './Credential';
import { Account } from '../../../../types/account';
import useCreateAccount from '../../hooks/useCreateAccount';
import useDeleteAccount from '../../hooks/useDeleteAccount';
import { classNames } from '../../../../helpers/strings';

type Props = {
  account: Account;
  index: number;
  updateAccounts: (index: number) => void;
};

const CredentialsList: React.FC<Props> = ({
  account,
  index,
  updateAccounts,
}) => {
  const { isCreating, errorOnCreate, createAccount } = useCreateAccount();
  const { deleteAccount } = useDeleteAccount();
  const initialState: any | undefined = account.connectedAccount?.credentials;
  const [credentials, setCredentials] = useState(initialState);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setCredentials(initialState);

    if (account.name) {
      setIsDirty(true);
    }
  }, [account.name, initialState]);

  const validatedCredentials = JSON.parse(
    JSON.stringify(credentials),
    (_, value) => value ?? value
  );

  const handleSubmitForm = (e: any): void => {
    e.preventDefault();

    // We only ever create accounts as the endpoint is idempotent i.e there is no concept of update/PUT
    createAccount({
      name: account.name,
      authType: account.authType,
      connectedAccount: {
        createdAt: Date.now(),
        credentials: validatedCredentials,
      },
    });
  };

  const handleChange = (e: any): void => {
    setCredentials({
      ...credentials,
      [e.target.name]: e.target.value,
    });

    setIsDirty(true);
  };

  const handleOnClick = () => {
    if (isConnected) {
      deleteAccount({
        name: account.name,
        authType: account.authType,
      });
    }
    updateAccounts(index);
  };

  const isConnected = account.connectedAccount?.createdAt !== 0;

  return (
    <form onSubmit={handleSubmitForm} className="col-span-3">
      <NameInput name={account.name} index={index} error={errorOnCreate} />
      {account.authType !== 'facebook' &&
        Object.keys(credentials).map(key => (
          <Credential
            key={`${key}-${index}`}
            index={index}
            name={key}
            value={credentials[key]}
            authType={account.authType}
            error={errorOnCreate}
            handleChange={handleChange}
            isDirty={isDirty}
          />
        ))}
      {account.authType === 'facebook' && (
        <InfoBanner message="Please note this will not be functional until Facebook approves the Virtual Lab application" />
      )}
      <div className="flex items-center py-3 justify-end">
        <div className="mr-1.5">
          <DeleteButton onClick={handleOnClick} />
        </div>
        <PrimaryButton
          type="submit"
          testId={`existing-account-submit-button-${index}`}
          loading={isCreating}
          leftIcon={isConnected ? 'RefreshIcon' : 'LinkIcon'}
        >
          {isConnected ? 'Update' : 'Connect'}
        </PrimaryButton>
      </div>
    </form>
  );
};

type NameInputProps = {
  name: string;
  index: number;
  error: string | undefined;
};

const NameInput: React.FC<NameInputProps> = ({ name, index, error }) => {
  return (
    <>
      <div className="flex flex-col mb-4">
        <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
          Name
        </label>
        <input
          id={`${name}-${index}`}
          name={name}
          type="text"
          className={classNames(
            'block w-full shadow-sm sm:text-sm rounded-md text-gray-600',
            (error ?? '').trim() !== ''
              ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
              : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
          )}
          placeholder={name}
          data-testid={`account-name-input-${index}`}
          value={name}
          disabled
        />
      </div>
    </>
  );
};

export default CredentialsList;
