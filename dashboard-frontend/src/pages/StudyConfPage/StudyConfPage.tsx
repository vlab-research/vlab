import { useState } from 'react';
import { useParams } from 'react-router-dom';
import PageLayout from '../../components/PageLayout';
import Form from '../NewStudyPage/components/form/Form';
import Navbar from './components/NavBar';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import useStudyConf from '../../hooks/useStudyConf';
import useStudy from '../../hooks/useStudy';
import general from './confs/general';
import recruitment from './confs/recruitment/base';
// import destinations from './confs/destinations/base';
import simpleList from './confs/simpleList';
import { ConfBase, ConfSelectBase, ConfListBase } from '../../types/conf';

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
  const confStore: Record<string, ConfBase | ConfSelectBase | ConfListBase> = {
    general,
    recruitment,
    // destinations,
    simpleList,
  };

  const confKeys = Object.keys(confStore);
  const confsToArr = Object.entries(confStore);
  const [index, setIndex] = useState<number>(0);
  const conf = confsToArr[index][1];

  return (
    <>
      <Navbar confKeys={confKeys} setIndex={setIndex} />
      <Form conf={conf} data={data} />
    </>
  );
};

export default StudyConfPage;
