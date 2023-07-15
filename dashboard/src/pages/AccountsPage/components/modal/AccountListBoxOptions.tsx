import { CheckIcon } from '@heroicons/react/solid';
import { Listbox } from '@headlessui/react';
import { AccountType } from './CreateAccountModal';

import { classNames, createLabelFor } from '../../../../helpers/strings';

type Props = {
  accounts: AccountType[];
};

const AccountListBoxOptions: React.FC<Props> = ({ accounts }) => {
  return (
    <Listbox.Options className="absolute z-10 max-h-56 w-4/5 overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
      {accounts.map((account: AccountType, index: number) => (
        <Listbox.Option
          key={`${account.authType}-${index}`}
          className={({ active }) =>
            classNames(
              active ? 'bg-indigo-600 text-white' : 'text-gray-700',
              'relative cursor-default select-none py-2 pl-3 pr-9'
            )
          }
          value={account.authType}
        >
          {({ selected, active }) => (
            <>
              <div className="flex items-center">
                <span
                  className={classNames(
                    selected ? 'font-semibold' : 'font-normal',
                    'ml-3 block truncate'
                  )}
                >
                  {createLabelFor(account.authType)}
                </span>
              </div>
              {selected ? (
                <span
                  className={classNames(
                    active ? 'text-white' : 'text-indigo-600',
                    'absolute inset-y-0 right-0 flex items-center px-4'
                  )}
                >
                  <CheckIcon className="h-5 w-5" aria-hidden="true" />
                </span>
              ) : null}
            </>
          )}
        </Listbox.Option>
      ))}
    </Listbox.Options>
  );
};

export default AccountListBoxOptions;
