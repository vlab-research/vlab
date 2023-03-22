import { useState } from 'react';
import PageLayout from '../../components/PageLayout';
import { create_study } from '../StudyConfPage/configs/create_study';
import { general } from '../StudyConfPage/configs/general';

import { Config } from '../../types/form';
import Navbar from '../../components/NavBar';
import simple from './controllers/simple';
import Form from './components/form/Form';

const StudyConfPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const configs: Record<string, Config> = {
    general,
  };

  const configsToArr = Object.entries(configs);
  const [index, setIndex] = useState<number>(0);
  const config: Config = configsToArr[index][1];
  const confKeys = Object.keys(configs).slice(1);

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
      {!isCreateStudyForm && <Navbar confKeys={confKeys} setIndex={setIndex} />}
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

export default StudyConfPage;
