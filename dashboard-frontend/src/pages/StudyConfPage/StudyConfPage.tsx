import { useState } from 'react';
import { useParams } from 'react-router-dom';
import PageLayout from '../../components/PageLayout';
import Navbar from './components/NavBar';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import { general } from './configs/general';
import useStudyConf from '../../hooks/useStudyConf';
import useStudy from '../../hooks/useStudy';
import { ConfBase } from '../../types/form';
import { assignComponentToConf } from '../../helpers/assignComponentToConf';

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
  const conf = assignComponentToConf(confsToArr[index][1]);

  const { Component } = conf;

  const isLast = index === confsToArr.length - 1 ? true : false;

  return (
    <>
      <Navbar confKeys={confKeys} setIndex={setIndex} />
      <Component {...conf} isLast={isLast} data={data} />
    </>
  );
};

export default StudyConfPage;
