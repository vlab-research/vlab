import { useState } from 'react';
import { useParams } from 'react-router-dom';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import Navbar from './components/NavBar';
import Form from '../../components/Form';
import General from './forms/general/General';
import Recruitment from './forms/recruitment/Recruitment';
import Destinations from './forms/destinations/Destinations';
import Creatives from './forms/creatives/Creatives';
import Variables from './forms/variables/Variables';
import Audiences from './forms/audience/Audiences';
import Strata from './forms/strata/Strata';
import useStudyConf from './hooks/useStudyConf';
import useStudy from '../StudyPage/hooks/useStudy';
import { CreateStudy as StudyType } from '../../types/conf';

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
      <PageContent data={studyConf.data} study={study} />
    </PageLayout>
  );
};

interface PageContentProps {
  data: any;
  study: StudyType;
}
const PageContent: React.FC<PageContentProps> = ({ data, study }) => {
  const formKeys = [
    'general',
    'recruitment',
    'destinations',
    'creatives',
    'audiences',
    'variables',
    'strata',
  ];
  const lookup = [
    General,
    Recruitment,
    Destinations,
    Creatives,
    Audiences,
    Variables,
    Strata,
  ];
  const [index, setIndex] = useState<number>(0);
  const id = formKeys[index];
  const component = lookup[index];
  return (
    <>
      <Navbar formKeys={formKeys} setIndex={setIndex} />
      <Form
        id={id}
        component={component}
        globalData={data}
        localData={data[id]}
        study={study}
      />
    </>
  );
};

export default StudyConfPage;
