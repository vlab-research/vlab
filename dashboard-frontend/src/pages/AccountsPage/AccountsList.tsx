import React from 'react';

import { AccountResource } from '../../types/account';
import { classNames } from '../../helpers/strings';

import { Link } from 'react-router-dom';
import InputToken from './InputToken';
import InputSecret from './InputSecret';

const AccountsList = ({ accounts }: { accounts: AccountResource[] }) => {
  return (
    <ListLayout>
      {accounts.map((account, index) => (
        <AccountListItem key={account.id} account={account} />
      ))}
    </ListLayout>
  );
};
const AccountListItem = ({ account }: { account: AccountResource }) => (
  <li>
    <div className="px-4 py-4 sm:px-6">
      <div className="flex flex-col sm:grid grid-cols-5 gap-4">
        <p className="text-sm font-medium text-indigo-600 truncate col-span-1">
          {account.name}
        </p>
        <div className="col-span-2 p-4">
          {account.authType === 'secret' ? <InputSecret /> : <InputToken />}
        </div>
        <button
          className={classNames(
            'sm:self-center items-center px-4 py-2 mx-4 col-span-1 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50'
          )}
        >
          <Link
            to={`/accounts/${account.slug}`}
            className="block hover:bg-gray-50"
          >
            Connect
          </Link>
        </button>
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
