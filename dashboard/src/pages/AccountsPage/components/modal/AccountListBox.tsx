import { Listbox } from '@headlessui/react';
import { ChevronDownIcon } from '@heroicons/react/solid';
import { AccountType } from './CreateAccountModal';
import AccountListBoxOptions from './AccountListBoxOptions';
import { createLabelFor } from '../../../../helpers/strings';

type Props = {
  accounts: AccountType[];
  selected: AccountType;
  handleSelectChange: (e: any) => void;
};

const AccountListBox: React.FC<Props> = ({
  accounts,
  selected,
  handleSelectChange,
}) => {
  return (
    <Listbox
      value={selected.authType}
      onChange={handleSelectChange}
      data-testid="account-type"
    >
      {() => (
        <>
          <Listbox.Label className="block mb-2 text-sm font-medium leading-6 text-gray-700">
            Account type
          </Listbox.Label>
          <Listbox.Button
            className="relative w-full cursor-default rounded-md bg-white py-2 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 sm:text-sm sm:leading-6"
            data-testid="account-type"
          >
            <span className="flex items-center">
              <span className="ml-3 block truncate">
                {createLabelFor(selected.authType)}
              </span>
            </span>
            <span className="pointer-events-none absolute inset-y-0 right-0 ml-3 flex items-center pr-2">
              <ChevronDownIcon
                className="h-5 w-5 text-gray-400"
                aria-hidden="true"
              />
            </span>
          </Listbox.Button>
          <AccountListBoxOptions accounts={accounts} />
        </>
      )}
    </Listbox>
  );
};

export default AccountListBox;
