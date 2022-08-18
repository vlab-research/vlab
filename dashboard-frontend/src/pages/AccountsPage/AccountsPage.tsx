import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import { queryCache } from 'react-query';
import AccountList, { AccountListSkeleton } from './AccountList';
import useAccounts from './useAccounts';

const AcccountsPage = () => (
  <PageLayout title={'Connected Accounts'}>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const { query, queryKey, connectedAccounts, errorMessage } = useAccounts();

  if (query.isLoading) {
    return <AccountListSkeleton numberItems={connectedAccounts.length} />;
  }

  if (query.isError) {
    return (
      <ErrorPlaceholder
        onClickTryAgain={() => queryCache.invalidateQueries(queryKey)}
        message={errorMessage}
      />
    );
  }

  return <AccountList connectedAccounts={connectedAccounts}></AccountList>;
};

export default AcccountsPage;
