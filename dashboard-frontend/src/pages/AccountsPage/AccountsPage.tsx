import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import { queryCache } from 'react-query';
import React, { useState } from 'react';
import AccountList, { AccountListSkeleton } from './AccountList';
import { Account } from '../../types/account';
import CreateAccountModal from './AccountCreateModal';
import PrimaryButton from '../../components/PrimaryButton';
import useAccounts from './useAccounts';

const AcccountsPage: React.FC<any> = () => {
  const [open, setOpen] = useState(false);
  return (
    <PageLayout
      title={'Connected Accounts'}
      topRightElements={<NewAccountButton open={open} setOpen={setOpen} />}
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
    return <AccountListSkeleton numberItems={accounts.length} />;
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
const NewAccountButton: React.FC<newAccountButtonsProps> = ({
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
