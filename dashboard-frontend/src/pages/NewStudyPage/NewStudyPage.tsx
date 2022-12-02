import { useCallback, useEffect, useState } from 'react';
import useCreateStudy from './useCreateStudy';
import PageLayout from '../../components/PageLayout';
import PrimaryButton from '../../components/PrimaryButton';
import Navbar from '../../components/NavBar';
import { Renderer } from './Renderer';
import { addOne } from '../../helpers/numbers';
import { general } from './configs/general';
import { destinations } from './configs/destinations/destinations';
import { recruitment } from './configs/recruitment/recruitment';
import { creative } from './configs/creative';
import { targeting } from './configs/targeting';
import { targeting_distribution } from './configs/targeting_distribution';
import { CreateStudyConfigData } from '../../types/study';
// import { createStateFromArrayOfTuples } from '../../helpers/createState';

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
  const [formData, setFormData] = useState({});
  const [index, setIndex] = useState(0);
  const config = configsToArr[index][1];
  const [currentConfig, setCurrentConfig] = useState(config);
  const { isCreating, errorOnCreate } = useCreateStudy();
  const { title } = config;
  // const megaState = createStateFromArrayOfTuples(some inital state);

  useEffect(() => {
    setCurrentConfig(config);
  }, [config]);

  const configKeys = Object.keys(configs);
  const isLast = index === configsToArr.length - 1 ? true : false;

  const handleClick = () => {
    if (isLast) {
      return;
    }
    setIndex(prevCount => addOne(prevCount));
  };

  const handleSubmitForm = (e: any) => {
    e.preventDefault();

    // const setInputVals = (arr: any[], key: string, e: any) => {
    //   const mapped = arr.map(el => ({
    //     [el[key]]: e.target.elements.el[key].value,
    //   }));
    //   return Object.assign({}, ...mapped);
    // };

    // createStudy({
    //   name: e.target.elements.name.value,
    //   objective: e.target.elements.objective.value,
    //   optimization_goal: e.target.elements.optimization_goal.value,
    //   destination_type: e.target.elements.destination_type.value,
    //   page_id: e.target.elements.page_id.value,
    //   instagram_id: e.target.elements.instagram_id.value,
    //   min_budget: e.target.elements.min_budget.value,
    //   opt_window: e.target.elements.opt_window.value,
    //   country: e.target.elements.country.value,
    //   ad_account: e.target.elements.ad_account.value,
    // });
  };

  const wrapperSetState = useCallback(val => {
    setFormData(val);
  }, []);

  return (
    <>
      <Navbar
        configs={configsToArr}
        configKeys={configKeys}
        setIndex={setIndex}
        setCurrentConfig={setCurrentConfig}
      />
      <div className="md:grid md:grid-cols-3 md:gap-6">
        <div className="md:col-span-1">
          <div className="px-4 sm:px-0"></div>
        </div>
        <div className="mt-5 md:mt-0 md:col-span-2">
          <form onSubmit={handleSubmitForm}>
            <div className="shadow overflow-hidden sm:rounded-md">
              <div className="px-4 py-5 bg-white sm:p-6">
                <div className="grid grid-cols-6 gap-6">
                  <div className="col-span-6 sm:col-span-5">
                    <h3 className="text-lg font-medium leading-6 text-gray-900">
                      {title}
                    </h3>
                    <Renderer
                      config={currentConfig}
                      erroroncreate={errorOnCreate}
                    />
                  </div>
                </div>
              </div>

              <div className="px-4 py-3 bg-gray-50 text-right sm:px-6">
                {!isLast ? (
                  <PrimaryButton
                    type="submit"
                    testId="new-study-next-button"
                    onClick={() => handleClick()}
                  >
                    Next
                  </PrimaryButton>
                ) : (
                  <PrimaryButton
                    type="submit"
                    loading={isCreating}
                    testId="new-study-submit-button"
                  >
                    Create
                  </PrimaryButton>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};

export default NewStudyPage;
