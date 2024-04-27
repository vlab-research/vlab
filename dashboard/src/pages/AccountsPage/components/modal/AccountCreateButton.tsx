import PrimaryButton from '../../../../components/PrimaryButton';

type Props = {
  authType: string;
};

const AccountCreateButton: React.FC<Props> = ({ authType }) => {
  const facebookHandler = () => {
    const clientID = process.env.REACT_APP_FACEBOOK_CLIENT_ID;
    const configId = process.env.REACT_APP_FACEBOOK_CONFIGURATION_ID;
    const redirect = `${window.location.href}?type=facebook`;
    const fb = `https://www.facebook.com/v16.0/dialog/oauth`;
    const state = 'fixmewitharealstate'
    const params = `client_id=${clientID}&config_id=${configId}&redirect_uri=${redirect}&state=${state}&response_type=code`;
    window.location.replace(`${fb}?${params}`);
  };

  if (authType === 'facebook') {
    return (
      <PrimaryButton
        leftIcon="LinkIcon"
        type="submit"
        testId="add-account-modal"
        className="ml-2"
        onClick={facebookHandler}
      >
        Connect
      </PrimaryButton>
    );
  }
  return (
    <PrimaryButton
      leftIcon="CheckCircleIcon"
      type="submit"
      testId="add-account-modal"
      className="ml-2"
    >
      Save
    </PrimaryButton>
  );
};

export default AccountCreateButton;
