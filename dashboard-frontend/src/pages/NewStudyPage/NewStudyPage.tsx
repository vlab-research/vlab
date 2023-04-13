import PageLayout from '../../components/PageLayout';
import Form from './components/form/Form';
import { create_study } from './configs/create_study';
import { ConfBase } from '../../types/conf';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const confStore: Record<string, ConfBase> = {
    create_study,
  };

  const confToArr = Object.entries(confStore);
  const conf: ConfBase = confToArr[0][1];

  return <Form conf={conf} />;
};

export default NewStudyPage;
