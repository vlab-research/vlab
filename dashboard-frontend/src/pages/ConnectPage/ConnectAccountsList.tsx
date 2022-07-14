import React from 'react';
import { AccountResource } from '../../types/account';
import { classNames } from '../../helpers/strings';

import { Link } from 'react-router-dom';

const ConnectedAcccountsList = ({
  accounts,
}: {
  accounts: AccountResource[];
}) => {
  return (
    <ListLayout>
      {accounts.map((account, index) => (
        <AccountListItem key={account.id} account={account} />
      ))}
    </ListLayout>
  );
};

const AccountListItem = ({
  account: { name, slug, authType },
}: {
  account: AccountResource;
}) => (
  <li>
    <div className="px-4 py-4 sm:px-6">
      <div className="flex flex-col sm:flex-row sm:items-center">
        <p className="text-sm font-medium text-indigo-600 truncate">{name}</p>

        {authType === 'secret' ? (
          <>
            <div className="flex flex-col mx-4 my-4 sm:my-0">
              <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                Enter client ID
              </label>
              <input
                type="text"
                className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
              ></input>
            </div>
            <div className="flex flex-col mx-4 my-4 sm:my-0">
              <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                Enter client secret
              </label>
              <input
                type="text"
                className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
              ></input>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col mx-4 my-4 sm:my-0">
              <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                Enter access token
              </label>
              <input
                type="text"
                className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
              ></input>
            </div>
          </>
        )}
        <button
          className={classNames(
            'sm:self-end items-center px-4 py-2 mx-4 my-4 sm:my-0 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50'
          )}
        >
          <Link to={`/connect/${slug}`} className="block hover:bg-gray-50">
            Connect
          </Link>
        </button>
      </div>
    </div>
  </li>
);

const ListLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200">{children}</ul>
  </div>
);

export default ConnectedAcccountsList;
