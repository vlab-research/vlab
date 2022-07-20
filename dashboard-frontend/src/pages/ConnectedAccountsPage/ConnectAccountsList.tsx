import React from 'react';

import { AccountResource } from '../../types/account';
import { classNames } from '../../helpers/strings';

import { Link } from 'react-router-dom';
import InputToken from './InputToken';
import InputSecret from './InputSecret';

const AccountListItem = ({
  account: { name, slug, authType },
}: {
  account: AccountResource;
}) => (
  <li>
    <div className="px-4 py-4 sm:px-6">
      <div className="flex flex-col sm:grid grid-cols-5 gap-4">
        <p className="text-sm font-medium text-indigo-600 truncate col-span-1">
          {name}
        </p>
        <div className="col-span-2 p-4">
          {authType === 'secret' ? <InputSecret /> : <InputToken />}
        </div>
        <button
          className={classNames(
            'sm:self-center items-center px-4 py-2 mx-4 col-span-1 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50'
          )}
        >
          <Link to={`/accounts/${slug}`} className="block hover:bg-gray-50">
            Connect
          </Link>
        </button>
      </div>
    </div>
  </li>
);

const ConnectedAcccountsList = ({
  accounts,
}: {
  accounts: AccountResource[];
}) => {
  return (
    <ListLayout>
      {accounts.map((account, index) => (
        <AccountListItem key={account.name} account={account} />
      ))}
    </ListLayout>
  );
};

const ListLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200">{children}</ul>
  </div>
);

export default ConnectedAcccountsList;
