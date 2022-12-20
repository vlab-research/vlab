import { useEffect, useState } from 'react';
import PageLayout from '../../components/PageLayout';
import Navbar from '../../components/NavBar';
import { Form } from './Form';
import { general } from './configs/general';
import { destinations } from './configs/destinations/destinations';
import { recruitment } from './configs/recruitment/recruitment';
import { creative } from './configs/creative';
import { targeting } from './configs/targeting';
import { targeting_distribution } from './configs/targeting_distribution';
import { CreateStudyConfigData } from '../../types/study';

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
  const [index, setIndex] = useState(0);
  const config = configsToArr[index][1];
  const [currentConfig, setCurrentConfig] = useState(config);
  const { title } = currentConfig;
  const configKeys = Object.keys(configs);
  const [formData, setFormData] = useState({});

  const updateState = (x: any) => {
    setFormData({ ...formData, [title]: x });
  };

  useEffect(() => {
    setCurrentConfig(config);
  }, [config]);

  const isLast = index === configsToArr.length - 1 ? true : false;

  return (
    <>
      <Navbar
        configs={configsToArr}
        configKeys={configKeys}
        setIndex={setIndex}
        setCurrentConfig={setCurrentConfig}
      />

      <Form
        config={currentConfig}
        getFormData={(x: any) => updateState(x)}
        isLast={isLast}
        setIndex={setIndex}
        title={title}
      />
    </>
  );
};

export default NewStudyPage;
