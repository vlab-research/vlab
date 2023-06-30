import { InfoBanner } from '../../../../components/InfoBanner';
import SecondaryButton from '../../../../components/SecondaryButton';
import { AccountType } from './CreateAccountModal';
import AccountCreateButton from './AccountCreateButton';
import AccountListBox from './AccountListBox';

type Props = {
  value: string;
  selected: AccountType;
  accounts: AccountType[];
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handleSubmit: (e: any) => void;
  handleOnChange: (e: any) => void;
  handleSelectChange: (e: any) => void;
  resetFormData: () => void;
};

const AccountForm: React.FC<Props> = ({
  value,
  selected,
  accounts,
  setOpen,
  handleSubmit,
  handleOnChange,
  handleSelectChange,
  resetFormData,
}) => {
  const handleOnCancelClick = () => {
    setOpen(false);
    resetFormData();
  };

  return (
    <form onSubmit={handleSubmit} className="col-span-4">
      <div className="w-full bg-white px-4 py-5">
        {selected.authType !== 'facebook' && (
          <div className="w-5/6 flex flex-col px-4 mb-4">
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
          </div>
        )}
        <div className="flex flex-col mb-4"></div>
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
