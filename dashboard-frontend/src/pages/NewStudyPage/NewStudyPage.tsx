import { useState } from 'react';
import PageLayout from '../../components/PageLayout';
import Navbar from '../../components/NavBar';
import Form from './form/components/Form';
import { general } from './form/configs/general';
import { destinations } from './form/configs/destinations/destinations';
import { recruitment } from './form/configs/recruitment/recruitment';
import { creative } from './form/configs/creative';
import { targeting } from './form/configs/targeting';
import { targeting_distribution } from './form/configs/targeting_distribution';
import { ConfigBase } from '../../types/form';
import simpleController from './form/controllers/simple';
import recruitmentController from './form/controllers/recruitment';
import destinationsController from './form/controllers/destinations';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const configs: Record<string, ConfigBase | any> = {
    general,
    destinations,
    recruitment,
    creative,
    targeting,
    targeting_distribution,
  };

  const configsToArr = Object.entries(configs);
  const [index, setIndex] = useState<number>(0);
  const config = configsToArr[index][1];
  const { title } = config;
  const configKeys = Object.keys(configs);
  const [formData, setFormData] = useState<any>({});

  const lookup: any = {
    configObject: simpleController,
    configSelect: recruitmentController,
    configList: destinationsController,
  };

  const str: keyof ConfigBase = 'type';

  const type = config[str];
  const controller = lookup[type];

  console.log(formData);

  if (!controller) {
    throw new Error(`Could not find form for controller type: ${type}`);
  }

  const updateFormData = (x: any) => {
    setFormData({ ...formData, [title]: x });
  };

  const isLast = index === configsToArr.length - 1 ? true : false;

  return (
    <>
      <Navbar configKeys={configKeys} setIndex={setIndex} />
      <Form
        controller={controller}
        config={config}
        isLast={isLast}
        setIndex={setIndex}
        updateFormData={updateFormData}
      />
    </>
  );
};

export default NewStudyPage;
