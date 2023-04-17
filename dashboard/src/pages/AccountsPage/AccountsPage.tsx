import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import { queryCache } from 'react-query';
import React, { useState, useEffect } from 'react';
import AccountList, { AccountListSkeleton } from './AccountList';
import { Account } from '../../types/account';
import CreateAccountModal from './AccountCreateModal';
import PrimaryButton from '../../components/PrimaryButton';
import useAccounts from './useAccounts';
import useGenerateFacebookAccount from './generateFacebookAccount';
import { useLocation } from 'react-router-dom';

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

type pageContentProps = {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

const PageContent: React.FC<pageContentProps> = ({ open, setOpen }) => {
  const { search } = useLocation();
  const { generateFacebookAccount } = useGenerateFacebookAccount();

  useEffect(() => {
    const values = new URLSearchParams(search.substring(search.indexOf('?')));
    if (values.get('type') === 'facebook' && values.get('code')) {
      // generate facebook account
      generateFacebookAccount({ code: values.get('code') });
    }
  }, [generateFacebookAccount, search]);

  // createAccounts is used to hold a list of accounts that has not been
  // added to the database, but instead is in an "intermediary" phase
  const [createAccounts, setCreateAccounts] = useState<Account[]>([]);

  const addAccountHandler = (account: Account) => {
    const newList = createAccounts.concat(account);
    setCreateAccounts(newList);
    setOpen(false);
  };

  // We need to clear the create accounts list once the account has been added
  // to the database
  const clearCreateAccounts = () => {
    setCreateAccounts([]);
  };

  const { query, queryKey, accounts, errorMessage } = useAccounts();

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
    <div>
      <CreateAccountModal
        open={open}
        setOpen={setOpen}
        addAccountHandler={addAccountHandler}
      />
      <AccountList
        accounts={[...createAccounts, ...accounts]}
        clearCreateAccounts={clearCreateAccounts}
      ></AccountList>
    </div>
  );
};

type newAccountButtonProps = {
  testId: string;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

// Component to open modal to create a new connected account
const NewAccountButton: React.FC<newAccountButtonProps> = ({
  testId,
  open,
  setOpen,
}) => {
  return (
    <PrimaryButton
      leftIcon="PlusIcon"
      testId="create-account"
      onClick={() => setOpen(!open)}
    >
      New Connected Account
    </PrimaryButton>
  );
};

export default AcccountsPage;
