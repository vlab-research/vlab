import { useState } from 'react';
import { useParams } from 'react-router-dom';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import Navbar from './components/NavBar';
import General from './forms/General';
import useStudyConf from '../../hooks/useStudyConf';
import useStudy from '../../hooks/useStudy';
import Form from '../NewStudyPage/components/form/Form';

const StudyConfPage = () => {
  const params = useParams<{ studySlug: string }>();
  const study = useStudy(params.studySlug);
  const studyConf = useStudyConf(params.studySlug);
  const data = studyConf.data;

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
      <PageContent data={data} />
    </PageLayout>
  );
};

const PageContent = (data: any) => {
  // TODO swap out "any" for a global form data type
  const formKeys = ['general'];
  const [index, setIndex] = useState<number>(0);
  const id = formKeys[index];
  const lookup = [General];
  const component = lookup[index];

  return (
    <>
      <Navbar formKeys={formKeys} setIndex={setIndex} />
      <Form id={id} component={component} {...data} />
    </>
  );
};

export default StudyConfPage;