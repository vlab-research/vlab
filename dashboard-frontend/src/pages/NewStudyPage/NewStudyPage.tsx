import PageLayout from '../../components/PageLayout';
import { ConfBase } from '../../types/form';
import Form from './components/form/Form';
import simple from './controllers/simple';
import { create_study } from './configs/create_study';

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

  const lookup: any = {
    confObject: simple,
  };

  const str: keyof ConfBase = 'type';

  const type = conf[str];
  const controller = lookup[type];

  if (!controller) {
    throw new Error(`Could not find form for controller type: ${type}`);
  }

  return <Form conf={conf} controller={controller} />;
};

export default NewStudyPage;
