import React, { useEffect, useState } from 'react';
import PrimaryButton from '../../../../components/PrimaryButton';
import SecondaryButton from '../../../../components/SecondaryButton';
import DeleteButton from '../../../../components/DeleteButton';
import { InfoBanner } from '../../../../components/InfoBanner';
import Credential from './Credential';
import { Account } from '../../../../types/account';
import { classNames } from '../../../../helpers/strings';

type Props = {
  account: Account;
  index: number;
  updateAccount: (account: Account) => void;
  deleteAccount: (account: Account) => void;

};

const CredentialsList: React.FC<Props> = ({
  account,
  index,
  updateAccount,
  deleteAccount,
}) => {
  const initialState: any | undefined = account.connectedAccount?.credentials;
  const [credentials, setCredentials] = useState(initialState);
  const [isDirty, setIsDirty] = useState(false);
  const [show, setShow] = useState(false);

  useEffect(() => {
    setCredentials(initialState);

    if (account.name) {
      setIsDirty(true);
    }
  }, [account.name, initialState]);


  const handleSubmitForm = (e: any): void => {
    e.preventDefault();
    updateAccount({ ...account, connectedAccount: { createdAt: account.connectedAccount?.createdAt || 0, credentials } });

  };

  const handleChange = (e: any): void => {
    setCredentials({
      ...credentials,
      [e.target.name]: e.target.value,
    });

    setIsDirty(true);
  };

  const handleDelete = () => {
    deleteAccount(account)
  };

  const isConnected = account.connectedAccount?.createdAt !== 0;

  return (
    <form onSubmit={handleSubmitForm} className="col-span-3">
      <NameInput name={account.name} index={index} error={undefined} />
      {account.authType !== 'facebook' &&
        Object.keys(credentials).map(key => (
          <Credential
            key={`${key}-${index}`}
            index={index}
            name={key}
            show={show}
            value={credentials[key]}
            authType={account.authType}
            error={undefined}
            handleChange={handleChange}
            isDirty={isDirty}
          />
        ))}
      {account.authType === 'facebook' && (
        <InfoBanner message="Please note this will not be functional until Facebook approves the Virtual Lab application" />
      )}
      <div className="flex items-center py-3 justify-end">
        <div className="mr-1.5">
          <DeleteButton onClick={handleDelete} />
        </div>
        <div className="mr-1.5">
          <SecondaryButton onClick={() => show ? setShow(false) : setShow(true)} >
            {show ? 'Hide' : 'Show'}
          </SecondaryButton>
        </div>
        <PrimaryButton
          type="submit"
          disabled={account.authType === 'api_key'}
          testId={`existing-account-submit-button-${index}`}
          loading={false}
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
            'block w-full shadow-sm sm:text-sm rounded-md text-gray-700 opacity-50 cursor-not-allowed',
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
