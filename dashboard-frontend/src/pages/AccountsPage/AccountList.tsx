import React from 'react';
import { AccountResource } from '../../types/account';
import { arrayMerge } from '../../helpers/arrays';
import PrimaryButton from '../../components/PrimaryButton';
import InputSecret from './InputSecret';
import InputToken from './InputToken';

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

const AccountListItem = ({
  account,
  index,
  errorMessage,
}: {
  account: AccountResource;
  index: number;
  errorMessage?: string;
}) => {
  return (
    <li data-testid="account-list-item">
      <div className="px-4 py-4 sm:px-6 py-6">
        <div className="flex flex-col sm:grid grid-cols-4 gap-4">
          <h2 className="text-sm font-medium text-indigo-600 truncate col-span-1">
            {account.name}
          </h2>
          <form>
            <div className="col-span-2">
              {account.authType === 'secret' ? (
                <InputSecret
                  account={
                    account.connectedAccount ? account.connectedAccount : null
                  }
                  index={index}
                  errorMessage={errorMessage}
                />
              ) : (
                <InputToken
                  account={
                    account.connectedAccount ? account.connectedAccount : null
                  }
                  index={index}
                  errorMessage={errorMessage}
                />
              )}
              {account.connectedAccount ? (
                <PrimaryButton
                  type="submit"
                  testId="existing-account-submit-button"
                >
                  Update
                </PrimaryButton>
              ) : (
                <PrimaryButton type="submit" testId="new-account-submit-button">
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
