import React, { useState } from 'react';
import { AccountResource } from '../../types/account';
import InputToken from './InputToken';
import InputSecret from './InputSecret';
import ConnectButton from '../../components/ConnectButton';
import { arrayMerge } from '../../helpers/arrays';
import useCreateAccount from './useCreateAccount';

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
    name: 'Some other account',
    authType: 'token',
  },
];

const AccountList = ({
  connectedAccounts,
}: {
  connectedAccounts: AccountResource[];
}) => {
  const allAccounts = arrayMerge(
    staticAccountResources,
    connectedAccounts,
    'name'
  );
  return (
    <ListLayout>
      {allAccounts.map((account, index) => (
        <AccountListItem key={account.name} account={account} index={index} />
      ))}
    </ListLayout>
  );
};

const testAccount = {
  name: 'Some other account',
  authType: 'token',
  connectedAccount: {
    createdAt: Date.now(),
    credentials: {
      token: 'some token', // TODO replace with formData
    },
  },
};

const AccountListItem = ({
  account,
  index,
}: {
  account: AccountResource;
  index: number;
}) => {
  const { query, queryKey, data, errorMessage } = useCreateAccount(testAccount);

  const initialFormData = {
    'client-id': '',
    'client-secret': '',
    token: '',
  };

  const [formData, setFormData] = useState({
    initialFormData,
  });

  const handleSubmit = (event: any) => {
    console.log('handleSubmit ran');
    event.preventDefault(); // prevent page refresh

    // 👇️ access input values here
    console.log('formData: ', formData);
  };

  return (
    <li data-testid="account-list-item">
      <div className="px-4 py-4 sm:px-6 py-6">
        <div className="flex flex-col sm:grid grid-cols-4 gap-4">
          <h2 className="text-sm font-medium text-indigo-600 truncate col-span-1">
            {account.name}
          </h2>
          <form onSubmit={handleSubmit}>
            <div className="col-span-2">
              {account.authType === 'secret' ? (
                <InputSecret
                  account={
                    account.connectedAccount ? account.connectedAccount : null
                  }
                  index={index}
                  setFormData={setFormData}
                />
              ) : (
                <InputToken
                  account={
                    account.connectedAccount ? account.connectedAccount : null
                  }
                  index={index}
                  setFormData={setFormData}
                />
              )}
              {account.connectedAccount ? (
                <ConnectButton
                  buttonLabel="update"
                  handleSubmit={handleSubmit}
                />
              ) : (
                <ConnectButton
                  buttonLabel="connect"
                  handleSubmit={handleSubmit}
                />
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
