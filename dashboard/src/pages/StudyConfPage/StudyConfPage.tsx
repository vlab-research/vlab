import { useParams } from 'react-router-dom';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import Sidebar from '../../components/Sidebar';
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
  const { conf } = useParams<{ conf: string }>();

  const lookup = [
    ['general', General],
    ['recruitment', Recruitment],
    ['destinations', Destinations],
    ['creatives', Creatives],
    ['audiences', Audiences],
    ['variables', Variables],
    ['strata', Strata],
  ];

  const id = conf;
  const index = lookup.findIndex(c => c[0] === conf);
  const component = lookup[index][1];
  const confKeys = lookup.map((c: any[]) => c[0]);

  return (
    <>
      <Sidebar />
      <Form
        id={id}
        component={component}
        globalData={data}
        localData={data[id]}
        study={study}
        confKeys={confKeys}
      />
    </>
  );
};

export default StudyConfPage;
