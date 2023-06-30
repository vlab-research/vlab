import React, { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import AccountForm from './AccountForm';
import { Account } from '../../../../types/account';

export type AccountType = {
  name: string;
  authType: string;
  credentials: any;
};

const accounts: AccountType[] = [
  {
    name: '',
    authType: 'typeform',
    credentials: {
      key: '',
    },
  },
  {
    name: '',
    authType: 'fly',
    credentials: {
      api_key: '',
    },
  },
  {
    name: '',
    authType: 'alchemer',
    credentials: {
      api_token: '',
      api_token_secret: '',
    },
  },
  {
    name: '',
    authType: 'facebook',
    credentials: {
      access_token: '',
      expires_in: 0,
      token_type: 'bearer',
    },
  },
];

type CreateAccountModalProps = {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handleModal: (a: Account) => void;
};

const CreateAccountModal: React.FC<CreateAccountModalProps> = ({
  open,
  setOpen,
  handleModal,
}) => {
  const [selected, setSelected] = useState<AccountType>(accounts[0]);

  const handleSelectChange = (e: any) => {
    const selectedAccount = accounts.find((a: AccountType) => a.authType === e);
    selectedAccount && setSelected(selectedAccount);
  };

  const handleOnChange = (e: any) => {
    const clone = { ...selected };
    clone.name = e.target.value;
    setSelected(clone);
  };

  const handleSubmit = (e: any) => {
    e.preventDefault();
    const account: Account = {
      name: selected.name,
      authType: selected.authType,
      connectedAccount: {
        createdAt: 0,
        credentials: selected.credentials,
      },
    };

    handleModal(account);
  };

  const resetFormData = () => {
    setSelected(accounts[0]);
  };

  const handleOnClose = () => {
    setOpen(false);
    resetFormData();
  };

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={handleOnClose}>
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
          <div className="flex min-h-full items-center justify-center">
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
                <div className="bg-white px-6 py-5">
                  <div className="flex flex-col w-full">
                    <Dialog.Title
                      as="h3"
                      className="mt-2 mx-2 text-base font-semibold leading-6 text-gray-700"
                    >
                      Add a connected account
                    </Dialog.Title>
                    <AccountForm
                      value={selected.name}
                      accounts={accounts}
                      selected={selected}
                      setOpen={setOpen}
                      handleSubmit={handleSubmit}
                      handleOnChange={handleOnChange}
                      handleSelectChange={handleSelectChange}
                      resetFormData={resetFormData}
                    />
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

export default CreateAccountModal;
