import { useState } from 'react';
import { useParams } from 'react-router-dom';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import Navbar from './components/NavBar';
import General from './forms/General';
import useStudyConf from '../../hooks/useStudyConf';
import useStudy from '../../hooks/useStudy';
import Form from './components/Form';

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
  const formKeys = ['general'];
  const [index, setIndex] = useState<number>(0);
  const id = formKeys[index];
  const lookup = [General];
  const component = lookup[index];
  const params = useParams<{ studySlug: string }>();
  const studyConf = useStudyConf(params.studySlug);

  return (
    <>
      <Navbar formKeys={formKeys} setIndex={setIndex} />
      <Form id={id} component={component} data={data.data[id]} />
    </>
  );
};

export default StudyConfPage;
