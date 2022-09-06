import React, { useState } from 'react';
import { Account } from '../../types/account';
import PrimaryButton from '../../components/PrimaryButton';
import InputAccountCredentials from './InputAccountCredentials';
import useCreateAccount from './useCreateAccount';

type accountListProps = {
  accounts: Account[];
  clearCreateAccounts: () => void;
};

const AccountList: React.FC<accountListProps> = ({
  accounts,
  clearCreateAccounts,
}) => {
  return (
    <ListLayout>
      {accounts.map((account, index) => (
        <AccountListItem
          key={account.authType}
          account={account}
          index={index}
          credentials={account.connectedAccount?.credentials}
          clearCreateAccounts={clearCreateAccounts}
        />
      ))}
    </ListLayout>
  );
};

type accountListItemProps = {
  account: Account;
  index: number;
  credentials: any;
  clearCreateAccounts: () => void;
};

const AccountListItem: React.FC<accountListItemProps> = ({
  account,
  index,
  credentials,
  clearCreateAccounts,
}) => {
  const { isCreating, errorOnCreate, createAccount } = useCreateAccount();
  const [credential, setCredential] = useState(credentials);

  // used to handle the state of the credentials attached
  // to the account
  function handleCredentialChange(e: any): void {
    setCredential({
      ...credential,
      [e.target.name]: e.target.value,
    });
  }

  const validateCredentials = JSON.parse(
    JSON.stringify(credential),
    (key, value) => value ?? value
  );

  const handleSubmitForm = (e: any): void => {
    e.preventDefault();

    const data = {
      name: account.name,
      authType: account.authType,
      connectedAccount: {
        createdAt: Date.now(),
        credentials: validateCredentials,
      },
    };
    clearCreateAccounts();
    // We only ever create accounts as the endpoint is
    // idempotent
    createAccount(data);
  };

  return (
    <li data-testid="account-list-item">
      <div className="px-4 py-4 sm:px-6 py-6">
        <div className="flex flex-col sm:grid sm:grid-cols-5 sm:gap-4">
          <h2 className="mb-4 text-sm font-medium text-indigo-600 truncate sm:mb-0 sm:col-span-1">
            {account.name}
          </h2>
          <form onSubmit={handleSubmitForm} className="col-span-3">
            <InputAccountCredentials
              error={errorOnCreate}
              handleCredentialChange={handleCredentialChange}
              index={index}
              entity={account.authType}
              credentials={credential}
            />
            <div className="flex items-baseline">
              <PrimaryButton
                type="submit"
                testId={`existing-account-submit-button-${index}`}
                loading={isCreating}
              >
                {account.connectedAccount ? 'Update' : 'Connect'}
              </PrimaryButton>
            </div>
          </form>
        </div>
      </div>
    </li>
  );
};

type accountListSkeletonProps = {
  number: number;
};

export const AccountListSkeleton: React.FC<accountListSkeletonProps> = ({
  number,
}) => (
  <ListLayout>
    <AccountListSkeletonItems number={number} />
  </ListLayout>
);

const AccountListSkeletonItems: React.FC<accountListSkeletonProps> = ({
  number,
}) => (
  <React.Fragment>
    {Array.from({ length: number }, (_, index) => (
      <li
        className="px-4 py-4 sm:px-6"
        data-testid="account-list-skeleton-item"
        key={index}
      >
        <div
          className="animate-pulse"
          style={{
            animationFillMode: 'backwards',
            animationDelay: `${150 * index}ms`,
          }}
        >
          <div className="h-5 bg-gray-200 rounded w-2/5"></div>
          <div className="mt-2 h-5 bg-gray-200 rounded w-1/5"></div>
        </div>
      </li>
    ))}
  </React.Fragment>
);

type listLayoutProps = {
  children: React.ReactNode;
};

const ListLayout: React.FC<listLayoutProps> = ({ children }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200" data-testid="account-list-item">
      {children}
    </ul>
  </div>
);

export default AccountList;
