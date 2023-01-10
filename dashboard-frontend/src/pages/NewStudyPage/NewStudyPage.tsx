import { useEffect, useState } from 'react';
import PageLayout from '../../components/PageLayout';
import Navbar from '../../components/NavBar';
import { general } from './configs/general';
import { destinations } from './configs/destinations/destinations';
import { recruitment } from './configs/recruitment/recruitment';
import { creative } from './configs/creative';
import { targeting } from './configs/targeting';
import { targeting_distribution } from './configs/targeting_distribution';
import { CreateStudyConfigData } from '../../types/study';
import ConfigSelect from './forms/ConfigSelect';
import ConfigList from './forms/ConfigList';
import ConfigObject from './forms/ConfigObject';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const configs: Record<string, CreateStudyConfigData | any> = {
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
    configObject: ConfigObject,
    configSelect: ConfigSelect,
    configList: ConfigList,
  };

  const str: keyof CreateStudyConfigData = 'type';

  const type = config[str];
  const Component = lookup[type];

  if (!Component) {
    throw new Error(`Could not find form for config type: ${type}`);
  }

  const updateFormData = (x: any) => {
    setFormData({ ...formData, [title]: x });
  };

  console.log(formData);

  const isLast = index === configsToArr.length - 1 ? true : false;

  return (
    <>
      <Navbar configKeys={configKeys} setIndex={setIndex} />
      <Component
        config={config}
        setIndex={setIndex}
        setFormData={updateFormData}
        isLast={isLast}
        title={title}
      />
    </>
  );
};

export default NewStudyPage;
