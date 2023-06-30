import React from 'react';
import Account from './Account';
import { Account as AccountType } from '../../../../types/account';

type AccountListProps = {
  accounts: AccountType[];
  updateAccounts: (index: number) => void;
};

const AccountList: React.FC<AccountListProps> = ({
  accounts,
  updateAccounts,
}) => {
  return (
    <ListLayout>
      {!accounts.length ? (
        <>
          <div className="p-2 m-4"></div>
          <div className="flex items-center justify-center h-40">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              className="flex-none fill-current text-gray-500 h-4 w-4"
            >
              <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm-.001 5.75c.69 0 1.251.56 1.251 1.25s-.561 1.25-1.251 1.25-1.249-.56-1.249-1.25.559-1.25 1.249-1.25zm2.001 12.25h-4v-1c.484-.179 1-.201 1-.735v-4.467c0-.534-.516-.618-1-.797v-1h3v6.265c0 .535.517.558 1 .735v.999z" />
            </svg>
            <p className="text-ml font-medium text-gray-700 ml-2">
              You currently have no connected accounts...
            </p>
          </div>
        </>
      ) : (
        accounts.map((account, index) => (
          <Account
            key={`${account.name}-${index}`}
            account={account}
            index={index}
            updateAccounts={updateAccounts}
          />
        ))
      )}
    </ListLayout>
  );
};

type AccountListSkeletonProps = {
  number: number;
};

export const AccountListSkeleton: React.FC<AccountListSkeletonProps> = ({
  number,
}) => (
  <ListLayout>
    <AccountListSkeletonItems number={number} />
  </ListLayout>
);

const AccountListSkeletonItems: React.FC<AccountListSkeletonProps> = ({
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

type ListLayoutProps = {
  children: React.ReactNode;
};

const ListLayout: React.FC<ListLayoutProps> = ({ children }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200" data-testid="account-list-item">
      {children}
    </ul>
  </div>
);

export default AccountList;
