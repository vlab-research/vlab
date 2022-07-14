import React from 'react';
import { AccountResource } from '../../types/account';

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
  account: { name, slug },
}: {
  account: AccountResource;
}) => (
  <li>
    <Link to={`/connect/${slug}`} className="block hover:bg-gray-50">
      <div className="px-4 py-4 sm:px-6">
        <div className="flex items-center">
          <p className="text-sm font-medium text-indigo-600 truncate">{name}</p>
        </div>
      </div>
    </Link>
  </li>
);

const ListLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200">{children}</ul>
  </div>
);

export default ConnectedAcccountsList;
