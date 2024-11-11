import { InfoBanner } from '../../../../components/InfoBanner';
import SecondaryButton from '../../../../components/SecondaryButton';
import { AccountType } from './CreateAccountModal';
import AccountCreateButton from './AccountCreateButton';
import AccountListBox from './AccountListBox';
import { useEffect } from 'react';
import Credential from '../accounts/Credential';

type Props = {
  value: string;
  selected: AccountType;
  accounts: AccountType[];
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  open: boolean;
  handleSubmit: (e: any) => void;
  handleOnChange: (e: any) => void;
  handleSelectChange: (e: any) => void;
  resetFormData: () => void;
};

// make this dynamic based on account type
// simplify the rest

const AccountForm: React.FC<Props> = ({
  value,
  selected,
  accounts,
  setOpen,
  open,
  handleSubmit,
  handleOnChange,
  handleSelectChange,
  resetFormData,
}) => {

  const handleOnCancelClick = () => {
    setOpen(false);
    resetFormData();
  };

  useEffect(() => {
    if (!open) {
      resetFormData();
    }
  }, [open, resetFormData]);


  const { credentials, authType } = selected

  return (
    <form onSubmit={handleSubmit} className="col-span-4">
      <div className="w-full bg-white px-4 py-5">
        <div className="w-5/6 flex flex-col px-4 mb-4">
          <AccountListBox
            accounts={accounts}
            selected={selected}
            handleSelectChange={handleSelectChange}
          />
          {selected.authType === 'facebook' && (
            <div className="mt-3">
              <InfoBanner message="Please note this will not be functional until Facebook approves the Virtual Lab application." />
            </div>
          )}
          {selected.authType !== 'facebook' && (
            <div className="mt-2.5">
              <label className="block mb-2 text-sm font-medium text-gray-700">
                Account name
              </label>
              <input
                id="name"
                name="account-name"
                data-testid="account-name"
                type="text"
                className="block w-full rounded-md border-0 py-2 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                placeholder="E.g typeform token 1"
                required
                onChange={handleOnChange}
                value={value}
              />
              {authType !== 'facebook' &&
                Object.keys(credentials).map((key, index) => (
                  <Credential
                    key={`${key}-${index}`}
                    index={index}
                    name={key}
                    show={true}
                    value={credentials[key]}
                    authType={authType}
                    error={undefined}
                    handleChange={handleOnChange}
                    isDirty={true}
                  />
                ))}


            </div>
          )}
        </div>

        <div className="pt-4 pb-2 px-6 sm:flex sm:flex-row-reverse">
          <AccountCreateButton authType={selected.authType} />
          <SecondaryButton onClick={handleOnCancelClick}>
            Cancel
          </SecondaryButton>
        </div>
      </div>
    </form>
  );
};

export default AccountForm;
