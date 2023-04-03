import { useState } from 'react';
import PageLayout from '../../components/PageLayout';
import { general } from './configs/general';
import Form from '../NewStudyPage/components/form/Form';
import simple from '../NewStudyPage/controllers/simple';
import Navbar from './components/NavBar';
import { useParams } from 'react-router-dom';
import useStudyConf from '../../hooks/useStudyConf';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import useStudy from '../../hooks/useStudy';
import { ConfBase } from '../../types/form';

const StudyConfPage = () => {
  const params = useParams<{ studySlug: string }>();
  const study = useStudy(params.studySlug);
  const studyConf = useStudyConf(params.studySlug);

  if (studyConf.errorOnLoad) {
    return (
      <PageLayout
        title={'Study configuration'}
        testId="study-conf-error-page"
        showBackButton
      >
        <ErrorPlaceholder
          message="Something went wrong while fetching your study configuration."
          onClickTryAgain={studyConf.refetchData}
        />
      </PageLayout>
    );
  }
  return (
    <PageLayout
      title={studyConf.isLoading ? 'Loading...' : study.name}
      testId="study-conf-page"
      showBackButton
    >
      <PageContent data={studyConf.data} />
    </PageLayout>
  );
};

const PageContent = (data: any) => {
  const confStore: Record<string, ConfBase> = {
    general,
  };

  const confKeys = Object.keys(confStore);
  const confsToArr = Object.entries(confStore);
  const [index, setIndex] = useState<number>(0);
  const conf: ConfBase = confsToArr[index][1];

  const lookup: any = {
    confObject: simple,
  };

  const str: keyof ConfBase = 'type';

  const type = conf[str];
  const controller = lookup[type];

  if (!controller) {
    throw new Error(`Could not find form for controller type: ${type}`);
  }

  const isLast = index === confsToArr.length - 1 ? true : false;

  return (
    <>
      <Navbar confKeys={confKeys} setIndex={setIndex} />
      <Form controller={controller} conf={conf} isLast={isLast} data={data} />
    </>
  );
};

export default StudyConfPage;
