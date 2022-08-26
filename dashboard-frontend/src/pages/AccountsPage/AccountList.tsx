import React from 'react';
import { AccountResource } from '../../types/account';
import { createSlugFor } from '../../helpers/strings';
import InputToken from './InputToken';
import InputSecret from './InputSecret';
import ConnectButton from '../../components/ConnectButton';
import { arrayMerge } from '../../helpers/arrays';

const createAccount = async () => {
  try {
    const res = await fetch('/accounts', {
      method: 'POST',
      body: JSON.stringify({ name: 'fly' }),
    });
    console.log(res);
  } catch (err) {
    console.log(err);
  }
};

const submitForm = async (event: any) => {
  event.preventDefault();
  createAccount();
  // if not connected POST else PUT
};

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

  // const [accounts, setAccounts] = useState(null);

  // const [accountName, setAccountName] = useState('');
  // const [credentials, setCredentials] = useState('');

  return (
    <ListLayout>
      {allAccounts.map((account, index) => (
        <AccountListItem
          key={account.name}
          account={account}
          slug={createSlugFor(account.name)}
          index={index}
        />
      ))}
    </ListLayout>
  );
};

const AccountListItem = ({
  account,
  slug,
  index,
}: {
  account: AccountResource;
  slug: string;
  index: number;
}) => (
  <li data-testid="account-list-item">
    <div className="px-4 py-4 sm:px-6 py-6">
      <div className="flex flex-col sm:grid grid-cols-4 gap-4">
        <p className="text-sm font-medium text-indigo-600 truncate col-span-1">
          {account.name}
        </p>
        <form onSubmit={submitForm}>
          <div className="col-span-2">
            {account.authType === 'secret' ? (
              <InputSecret
                account={
                  account.connectedAccount ? account.connectedAccount : null
                }
                index={index}
              />
            ) : (
              <InputToken
                account={
                  account.connectedAccount ? account.connectedAccount : null
                }
                index={index}
              />
            )}
            {account.connectedAccount ? (
              <ConnectButton buttonLabel="update" slug={slug} />
            ) : (
              <ConnectButton buttonLabel="connect" slug={slug} />
            )}
          </div>
        </form>
      </div>
    </div>
  </li>
);

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
