import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import CreateAccountModal from './components/modal/CreateAccountModal';
import NewAccountButton from './components/accounts/NewAccountButton';
import AccountList, {
  AccountListSkeleton,
} from './components/accounts/AccountList';
import useAccounts from './hooks/useAccounts';
import useCreateAccount from './hooks/useCreateAccount';
import useCreateFacebookAccount from './hooks/useCreateFacebookAccount';
import useDeleteAccount from './hooks/useDeleteAccount';
import { Account } from '../../types/account';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';


const AcccountsPage: React.FC<any> = () => {
  const [open, setOpen] = useState(false);

  return (
    <PageLayout
      title={'Connected Accounts'}
      topRightElements={
        <NewAccountButton
          open={open}
          setOpen={setOpen}
          testId="new-account-button"
        />
      }
    >
      <PageContent open={open} setOpen={setOpen} />
    </PageLayout>
  );
};

type PageContentProps = {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

const PageContent: React.FC<PageContentProps> = ({ open, setOpen }) => {
  const { search } = useLocation();

  const { query, queryKey, queryClient, accounts, errorMessage } = useAccounts();
  const { generateApiKey } = useAuthenticatedApi();

  const onSettled = () => {
    queryClient.invalidateQueries({ queryKey: [queryKey] })
    setOpen(false)
  }

  const { isCreating, createAccount } = useCreateAccount(onSettled);
  const { isDeleting, deleteAccount } = useDeleteAccount(onSettled);
  const { isCreating: facebookCreating, createFacebookAccount } = useCreateFacebookAccount(onSettled);

  useEffect(() => {
    const values = new URLSearchParams(search.substring(search.indexOf('?')));
    if (values.get('type') === 'facebook' && values.get('code')) {
      createFacebookAccount({ code: values.get('code') });
    }
  }, [createFacebookAccount, search]);

  const facebookHandler = () => {
    const clientID = process.env.REACT_APP_FACEBOOK_CLIENT_ID;
    const configId = process.env.REACT_APP_FACEBOOK_CONFIGURATION_ID;
    const redirect = `${window.location.href}?type=facebook`;
    const fb = `https://www.facebook.com/v16.0/dialog/oauth`;
    const params = `client_id=${clientID}&config_id=${configId}&redirect_uri=${redirect}&response_type=code`;
    window.location.replace(`${fb}?${params}`);
  };

  const createOrUpdateAccount = async (account: Account) => {

    if (account.authType === 'facebook') {
      return facebookHandler()
    }

    if (account.authType === 'api_key') {
      const res = await generateApiKey({ name: account.name })
      const { token, id } = res.data
      account.connectedAccount = { createdAt: 0, credentials: { token, id } }
    }

    const validatedCredentials = JSON.parse(
      JSON.stringify(account?.connectedAccount?.credentials),
      (_, value) => value ?? value
    );

    createAccount({
      name: account.name,
      authType: account.authType,
      connectedAccount: {
        createdAt: Date.now(),
        credentials: validatedCredentials,
      },
    });
  }


  if (query.isLoading || isCreating || isDeleting || facebookCreating) {
    return <AccountListSkeleton number={accounts.length} />;
  }

  if (query.isError) {
    return (
      <ErrorPlaceholder
        onClickTryAgain={query.refetch}
        message={errorMessage}
      />
    );
  }

  return (
    <>
      <CreateAccountModal
        open={open}
        setOpen={setOpen}
        handleModal={createOrUpdateAccount}
      />
      <AccountList
        accounts={accounts}
        deleteAccount={deleteAccount}
        updateAccount={createOrUpdateAccount}
      ></AccountList>
    </>
  );
};

export default AcccountsPage;
