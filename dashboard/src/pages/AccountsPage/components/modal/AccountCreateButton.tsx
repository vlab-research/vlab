import PrimaryButton from '../../../../components/PrimaryButton';

type Props = {
  authType: string;
};

const AccountCreateButton: React.FC<Props> = ({ authType }) => {

  return (
    <PrimaryButton
      leftIcon="CheckCircleIcon"
      type="submit"
      testId="add-account-modal"
      className="ml-2"
    >
      {authType === 'facebook' ? 'Connect' : 'Save'}
    </PrimaryButton>
  );
};

export default AccountCreateButton;
