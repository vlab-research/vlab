import React from 'react';
import { Account } from '../../types/account';
import InputAccountCredentials from './InputAccountCredentials';

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
      {!accounts.length ? (
        <>
          <div className="p-2 m-4"></div>
          <div className="flex items-center justify-center h-40">
            <p className="text-lg font-medium text-indigo-600 m-4">
              You currently have no connected accounts...
            </p>
          </div>
        </>
      ) : (
        accounts.map((account, index) => (
          <AccountListItem
            key={account.authType}
            account={account}
            index={index}
            credentials={account.connectedAccount?.credentials}
            clearCreateAccounts={clearCreateAccounts}
          />
        ))
      )}
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
  clearCreateAccounts,
}) => {
  return (
    <li data-testid="account-list-item">
      <div className="px-4 py-4 sm:px-6 py-6">
        <div className="flex flex-col sm:grid sm:grid-cols-5 sm:gap-4">
          <h2 className="mb-4 text-sm font-medium text-indigo-600 truncate sm:mb-0 sm:col-span-1">
            {account.name}
          </h2>
          <InputAccountCredentials
            clearCreateAccounts={clearCreateAccounts}
            index={index}
            account={account}
          />
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
