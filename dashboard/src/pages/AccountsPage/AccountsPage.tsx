import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { queryCache } from 'react-query';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import CreateAccountModal from './components/modal/CreateAccountModal';
import NewAccountButton from './components/accounts/NewAccountButton';
import AccountList, {
  AccountListSkeleton,
} from './components/accounts/AccountList';
import useAccounts from './hooks/useAccounts';
import useCreateFacebookAccount from './hooks/useCreateFacebookAccount';
import { Account } from '../../types/account';

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
  const { createFacebookAccount } = useCreateFacebookAccount();

  useEffect(() => {
    const values = new URLSearchParams(search.substring(search.indexOf('?')));
    if (values.get('authType') === 'facebook' && values.get('code')) {
      createFacebookAccount({ code: values.get('code') });
    }
  }, [createFacebookAccount, search]);

  const { query, queryKey, accounts, errorMessage } = useAccounts();

  const [state, setAccounts] = useState<Account[]>(accounts);

  useEffect(() => {
    setAccounts(accounts);
  }, [accounts]);

  const handleModal = (account: Account) => {
    const newArr = [account, ...state];
    setAccounts(newArr);
    setOpen(false);
  };

  const updateAccounts = (index: number) => {
    const newArr = accounts.filter((a: Account, i: number) => index !== i);
    setAccounts(newArr);
  };

  if (query.isLoading) {
    return <AccountListSkeleton number={accounts.length} />;
  }

  if (query.isError) {
    return (
      <ErrorPlaceholder
        onClickTryAgain={async () => {
          await queryCache.invalidateQueries(queryKey);
        }}
        message={errorMessage}
      />
    );
  }

  return (
    <>
      <CreateAccountModal
        open={open}
        setOpen={setOpen}
        handleModal={handleModal}
      />
      <AccountList
        accounts={state}
        updateAccounts={updateAccounts}
      ></AccountList>
    </>
  );
};

export default AcccountsPage;
