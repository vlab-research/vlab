import React, { Fragment, useState } from 'react';
import { Dialog, Transition, Listbox } from '@headlessui/react';
import PrimaryButton from '../../components/PrimaryButton';
import SecondaryButton from '../../components/SecondaryButton';

import { Account } from '../../types/account';
import { CheckIcon } from '@heroicons/react/solid';
import { ChevronDownIcon } from '@heroicons/react/solid';
import { classNames } from '../../helpers/strings';

// general structures of the account types
// used to boostrap an empty account
// TODO: see if there is a way to use types here
const accountTypes = [
  {
    name: 'Typeform',
    type: 'typeform',
    credentials: {
      key: '',
    },
  },
  {
    name: 'Fly',
    type: 'fly',
    credentials: {
      api_key: '',
    },
  },
  {
    name: 'Alchemer',
    type: 'alchemer',
    credentials: {
      api_token: '',
      api_token_secret: '',
    },
  },
];

type createAccountModalProps = {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  addAccountHandler: (a: Account) => void;
};

const CreateAccountModal: React.FC<createAccountModalProps> = ({
  open,
  setOpen,
  addAccountHandler,
}) => {
  const [selected, setSelected] = useState(accountTypes[1]);

  const handleSubmit = (e: any) => {
    e.preventDefault();
    const account: Account = {
      name: selected.type,
      authType: e.target.identifier.value,
      connectedAccount: {
        createdAt: Date.now(),
        credentials: selected.credentials,
      },
    };
    addAccountHandler(account);
  };

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={setOpen}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start">
                    <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                      <Dialog.Title
                        as="h3"
                        className="text-base font-semibold leading-6 text-gray-900"
                      >
                        New Connected Account
                      </Dialog.Title>
                      <AccountForm
                        open={open}
                        selected={selected}
                        setSelected={setSelected}
                        handleSubmit={handleSubmit}
                        setOpen={setOpen}
                      />
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
};

type accountFormProps = {
  handleSubmit: (e: any) => void;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  selected: any;
  setSelected: React.Dispatch<React.SetStateAction<any>>;
};

const AccountForm: React.FC<accountFormProps> = ({
  handleSubmit,
  open,
  selected,
  setSelected,
  setOpen,
}) => {
  return (
    <form onSubmit={handleSubmit} className="col-span-3">
      <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
        <div className="flex flex-col mb-4">
          <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
            Name
          </label>
          <input
            id="name"
            name="identifier"
            data-testid="account-name"
            type="text"
            className="block w-full rounded-md border-0 py-1.5 pl-7 pr-20 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
            placeholder="Give your connected account a name"
          />
        </div>
        <div className="flex flex-col mb-4"></div>
        <AccountListBox
          selected={selected}
          setSelected={setSelected}
          open={open}
        />
        <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
          <PrimaryButton
            leftIcon="PlusIcon"
            type="submit"
            testId="add-account-modal"
          >
            Add
          </PrimaryButton>
          &nbsp;&nbsp;&nbsp;
          <SecondaryButton onClick={() => setOpen(false)}>
            cancel
          </SecondaryButton>
        </div>
      </div>
    </form>
  );
};

type accountListBoxProps = {
  selected: any;
  setSelected: React.Dispatch<React.SetStateAction<any>>;
  open: boolean;
};

const AccountListBox: React.FC<accountListBoxProps> = ({
  selected,
  setSelected,
  open,
}) => {
  return (
    <Listbox value={selected} onChange={setSelected} data-testid="account-type">
      {({ open }) => (
        <>
          <Listbox.Label className="block text-sm font-medium leading-6 text-gray-900">
            Type
          </Listbox.Label>
          <div className="relative mt-2">
            <Listbox.Button
              className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 sm:text-sm sm:leading-6"
              data-testid="account-type"
            >
              <span className="flex items-center">
                <span className="ml-3 block truncate">{selected.name}</span>
              </span>
              <span className="pointer-events-none absolute inset-y-0 right-0 ml-3 flex items-center pr-2">
                <ChevronDownIcon
                  className="h-5 w-5 text-gray-400"
                  aria-hidden="true"
                />
              </span>
            </Listbox.Button>
            <AccountListBoxOptions selected={selected} />
          </div>
        </>
      )}
    </Listbox>
  );
};

type accountListBoxOptionsProps = {
  selected: any;
};

const AccountListBoxOptions: React.FC<accountListBoxOptionsProps> = ({
  selected,
}) => {
  return (
    <Listbox.Options className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
      {accountTypes.map(accountType => (
        <Listbox.Option
          key={accountType.name}
          className={({ active }) =>
            classNames(
              active ? 'bg-indigo-600 text-white' : 'text-gray-900',
              'relative cursor-default select-none py-2 pl-3 pr-9'
            )
          }
          value={accountType}
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
                  {accountType.name}
                </span>
              </div>
              {selected ? (
                <span
                  className={classNames(
                    active ? 'text-white' : 'text-indigo-600',
                    'absolute inset-y-0 right-0 flex items-center pr-4'
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

export default CreateAccountModal;
