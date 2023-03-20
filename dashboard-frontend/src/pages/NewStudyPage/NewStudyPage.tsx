import { useState } from 'react';
import PageLayout from '../../components/PageLayout';
import Form from './form/components/Form';
import { create_study } from './form/configs/create_study';
import { general } from './form/configs/general';

import { Config } from '../../types/form';
import simple from './form/controllers/simple';
import Navbar from '../../components/NavBar';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const configs: Record<string, Config> = {
    create_study,
    general,
  };

  const configsToArr = Object.entries(configs);
  const [index, setIndex] = useState<number>(0);
  const config: Config = configsToArr[index][1];
  const configKeys = Object.keys(configs);

  const lookup: any = {
    configObject: simple,
  };

  const str: keyof Config = 'type';

  const type = config[str];
  const controller = lookup[type];

  if (!controller) {
    throw new Error(`Could not find form for controller type: ${type}`);
  }

  const isLast = index === configsToArr.length - 1 ? true : false;

  const isCreateStudyForm = config === create_study ? true : false;

  return (
    <>
      {!isCreateStudyForm && (
        <Navbar configKeys={configKeys} setIndex={setIndex} />
      )}
      <Form
        controller={controller}
        config={config}
        isLast={isLast}
        isCreateStudyForm={isCreateStudyForm}
        setIndex={setIndex}
      />
    </>
  );
};

export default NewStudyPage;
