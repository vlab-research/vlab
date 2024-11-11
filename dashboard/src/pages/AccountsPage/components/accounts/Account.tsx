import CredentialsList from './CredentialsList';
import { createLabelFor } from '../../../../helpers/strings';
import { Account as AccountType } from '../../../../types/account';

type AccountProps = {
  account: AccountType;
  index: number;
  updateAccount: (account: AccountType) => void;
  deleteAccount: (account: AccountType) => void;
};

const Account: React.FC<AccountProps> = ({
  account,
  index,
  updateAccount,
  deleteAccount,
}) => {
  return (
    <li data-testid="account-list-item">
      <div className="px-4 py-4 sm:px-6 py-6">
        <div className="sm:grid sm:grid-cols-5 sm:gap-4">
          <div>
            <h2 className="mb-4 text-l font-medium text-indigo-600 truncate sm:mb-0 sm:col-span-1">
              {account.name}
            </h2>
            <p className="mt-1 italic text-gray-700 text-xs">
              {createLabelFor(account.authType)}
            </p>
          </div>
          <CredentialsList
            account={account}
            index={index}
            updateAccount={updateAccount}
            deleteAccount={deleteAccount}
          />
        </div>
      </div>
    </li>
  );
};

export default Account;
