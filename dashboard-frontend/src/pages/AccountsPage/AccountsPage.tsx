import ErrorPlaceholder, {
  Explanation,
  PlaceholderLayout,
} from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import { queryCache } from 'react-query';
import AccountsList, { AccountListSkeleton } from './AccountsList';
import useAccounts from './useAccounts';

const AcccountsPage = () => (
  <PageLayout title={'Connected Accounts'}>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const { query, queryKey, accounts, errorMessage } = useAccounts();

  if (query.isLoading) {
    return <AccountListSkeleton numberItems={accounts.length} />;
  }

  if (query.isError) {
    return (
      <ErrorPlaceholder
        onClickTryAgain={() => queryCache.invalidateQueries(queryKey)}
        message={errorMessage}
      />
    );
  }

  if (!accounts.length) {
    return <NoAccountsPlaceholder />;
  }

  return <AccountsList accounts={accounts}></AccountsList>;
};

const NoAccountsPlaceholder = () => (
  <PlaceholderLayout>
    <Explanation>Oops, no accounts found!</Explanation>
  </PlaceholderLayout>
);

export default AcccountsPage;
