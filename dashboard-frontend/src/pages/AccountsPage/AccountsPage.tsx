import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import PageLayout from '../../components/PageLayout';
import { queryCache } from 'react-query';
import AcccountsList from './AccountsList';
import useAccounts from './useAccounts';

const AcccountsPage = () => (
  <PageLayout title={'Connected Accounts'}>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const { query, queryKey, accounts, errorMessage } = useAccounts();

  if (query.isError) {
    return (
      <ErrorPlaceholder
        onClickTryAgain={() => queryCache.invalidateQueries(queryKey)}
        message={errorMessage}
      />
    );
  }

  return <AcccountsList accounts={accounts}></AcccountsList>;
};

export default AcccountsPage;
