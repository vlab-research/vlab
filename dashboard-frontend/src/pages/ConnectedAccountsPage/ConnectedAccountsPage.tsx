import PageLayout from '../../components/PageLayout';
import ConnectedAcccountsList from './ConnectAccountsList';

const accounts = [
  { id: '1', name: 'Fly', slug: 'fly', authType: 'secret' },
  { id: '2', name: 'Typeform', slug: 'typeform', authType: 'token' },
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
