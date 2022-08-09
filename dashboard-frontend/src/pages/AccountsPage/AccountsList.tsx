import React from 'react';

import { AccountResource } from '../../types/account';
import { createSlugFor } from '../../helpers/strings';

import InputToken from './InputToken';
import InputSecret from './InputSecret';
import ConnectButton from '../../components/ConnectButton';

const AccountsList = ({ accounts }: { accounts: AccountResource[] }) => {
  return (
    <ListLayout>
      {accounts.map((account, index) => (
        <AccountListItem
          key={account.name}
          account={account}
          slug={createSlugFor(account.name)}
        />
      ))}
    </ListLayout>
  );
};
const AccountListItem = ({
  account,
  slug,
}: {
  account: AccountResource;
  slug: string;
}) => (
  <li>
    <div className="px-4 py-4 sm:px-6 py-6">
      <div className="flex flex-col sm:grid grid-cols-4 gap-4">
        <p className="text-sm font-medium text-indigo-600 truncate col-span-1">
          {account.name}
        </p>
        <div className="col-span-2">
          {account.authType === 'secret' ? (
            <InputSecret
              account={
                account.connectedAccount ? account.connectedAccount : null
              }
            />
          ) : (
            <InputToken
              account={
                account.connectedAccount ? account.connectedAccount : null
              }
            />
          )}
          {account.connectedAccount ? (
            <ConnectButton buttonLabel="Update" slug={slug} />
          ) : (
            <ConnectButton buttonLabel="Connect" slug={slug} />
          )}
        </div>
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
        data-testid="study-list-skeleton-item"
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

export default AccountsList;
