import PageLayout from '../../components/PageLayout';
import ConnectedAcccountsList from './ConnectAccountsList';

const accounts = [
  { id: '1', name: 'Fly', slug: 'fly' },
  { id: '2', name: 'Typeform', slug: 'typeform' },
];

const ConnectedAcccountsPage = () => (
  <PageLayout title={'Connected Accounts'}>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  return <ConnectedAcccountsList accounts={accounts} />;
};

export default ConnectedAcccountsPage;
