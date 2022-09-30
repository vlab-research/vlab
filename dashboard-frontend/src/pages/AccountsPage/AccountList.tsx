import React, { useState } from 'react';
import { AccountResource } from '../../types/account';
import { arrayMerge } from '../../helpers/arrays';
import PrimaryButton from '../../components/PrimaryButton';
import InputSecret from './InputSecret';
import InputToken from './InputToken';
import useCreateAccount from './useCreateAccount';
import useUpdateAccount from './useUpdateAccount';

const staticAccountResources = [
  {
    name: 'Fly',
    authType: 'secret',
  },
  {
    name: 'Typeform',
    authType: 'token',
  },
  {
    name: 'Test',
    authType: 'token',
  },
];

const AccountList = ({ accounts }: { accounts: AccountResource[] }) => {
  const allAccounts = arrayMerge(staticAccountResources, accounts, 'name');

  return (
    <ListLayout>
      {allAccounts.map((account, index) => (
        <AccountListItem
          key={account.name}
          account={account}
          index={index}
          clientId={account.connectedAccount?.credentials.clientId}
          clientSecret={account.connectedAccount?.credentials.clientSecret}
          token={account.connectedAccount?.credentials.token}
        />
      ))}
    </ListLayout>
  );
};

const AccountListItem = ({
  account,
  index,
  clientId,
  clientSecret,
  token,
}: {
  account: AccountResource;
  index: number;
  clientId: string;
  clientSecret: string;
  token: string;
}) => {
  const { isCreating, errorOnCreate, createAccount } = useCreateAccount();
  const { isUpdating, errorOnUpdate, updateAccount } = useUpdateAccount();

  const [credentials, setCredentials] = useState({
    clientId: clientId ? clientId : '',
    clientSecret: clientSecret ? clientSecret : '',
    token: token ? token : '',
  });

  function handleChange(e: any) {
    const value = e.target.value;

    setCredentials({
      ...credentials,
      [e.target.name]: value,
    });
  }

  const validateCredentials = JSON.parse(
    JSON.stringify(credentials),
    (key, value) => (value === null || value === '' ? undefined : value)
  );

  const handleSubmitForm = (e: any) => {
    e.preventDefault();

    const data = {
      name: account.name,
      authType: account.authType,
      connectedAccount: {
        createdAt: Date.now(),
        credentials: validateCredentials,
      },
    };

    account.connectedAccount ? updateAccount(data) : createAccount(data);
  };

  return (
    <li data-testid="account-list-item">
      <div className="px-4 py-4 sm:px-6 py-6">
        <div className="flex flex-col sm:grid sm:grid-cols-5 sm:gap-4">
          <h2 className="mb-4 text-sm font-medium text-indigo-600 truncate sm:mb-0 sm:col-span-1">
            {account.name}
          </h2>
          <form onSubmit={handleSubmitForm} className="col-span-3">
            {account.authType === 'secret' ? (
              <InputSecret
                error={errorOnCreate || errorOnUpdate}
                handleChange={handleChange}
                index={index}
                clientId={credentials.clientId}
                clientSecret={credentials.clientSecret}
              />
            ) : (
              <InputToken
                error={errorOnCreate || errorOnUpdate}
                handleChange={handleChange}
                index={index}
                token={credentials.token}
              />
            )}
            <div className="flex items-baseline">
              {account.connectedAccount ? (
                <PrimaryButton
                  type="submit"
                  testId={`existing-account-submit-button-${index}`}
                  loading={isUpdating}
                >
                  Update
                </PrimaryButton>
              ) : (
                <PrimaryButton
                  type="submit"
                  testId={`new-account-submit-button-${index}`}
                  loading={isCreating}
                >
                  Connect
                </PrimaryButton>
              )}
            </div>
          </form>
        </div>
      </div>
    </li>
  );
};

export const AccountListSkeleton = ({
  numberItems,
}: {
  numberItems: number;
}) => (
  <ListLayout>
    <AccountListSkeletonItems number={numberItems} />
  </ListLayout>
);

const AccountListSkeletonItems = ({ number }: { number: number }) => (
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

const ListLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200">{children}</ul>
  </div>
);

export default AccountList;
