import PageLayout from '../../components/PageLayout';
import CreateStudy from './form/CreateStudy';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  return <CreateStudy />;
};

export default NewStudyPage;
