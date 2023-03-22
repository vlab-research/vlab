import PageLayout from '../../components/PageLayout';
import { create_study } from '../StudyConfPage/configs/create_study';

import { Config } from '../../types/form';
import simple from '../StudyConfPage/controllers/simple';
import Form from '../StudyConfPage/components/form/Form';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const configs: Record<string, Config> = {
    create_study,
  };

  const configToArr = Object.entries(configs);
  const config: Config = configToArr[0][1];

  const lookup: any = {
    configObject: simple,
  };

  const str: keyof Config = 'type';

  const type = config[str];
  const controller = lookup[type];

  if (!controller) {
    throw new Error(`Could not find form for controller type: ${type}`);
  }

  const isCreateStudyForm = config === create_study ? true : false;

  return (
    <Form
      controller={controller}
      config={config}
      isCreateStudyForm={isCreateStudyForm}
    />
  );
};

export default NewStudyPage;
