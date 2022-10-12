import { useCallback, useMemo, useState } from 'react';
import useCreateStudy from './useCreateStudy';
import PageLayout from '../../components/PageLayout';
import PrimaryButton from '../../components/PrimaryButton';

import { Renderer } from './Renderer';
import { getConfig } from './getConfig';
import { general } from './configs/general';
import { destination } from './configs/destination';
import { recruitment_sample } from './configs/recruitment_simple';
import { recruitment_destination_experiment } from './configs/recruitment_destination_experiment';
import { recruitment_pipeline_experiment } from './configs/recruitment_pipeline_experiment';
import { creative } from './configs/creative';
import { targeting } from './configs/targeting';
import { targeting_distribution } from './configs/targeting_distribution';
import { createLabelFor } from '../../helpers/strings';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const { isCreating, errorOnCreate, createStudy } = useCreateStudy();

  const [state, setState] = useState({
    name: '',
    objective: '',
    optimization_goal: '',
    destination_type: '',
    page_id: '',
    instagram_id: '',
    min_budget: '',
    opt_window: '',
    ad_account: '',
    country: '',
  });

  // wrapper function to give to child
  const wrapperSetState = useCallback(
    val => {
      setState(val);
    },
    [setState]
  );

  const handleSubmitForm = (e: any) => {
    e.preventDefault();

    createStudy({
      name: e.target.elements.name.value,
      objective: e.target.elements.objective.value,
      optimization_goal: e.target.elements.optimization_goal.value,
      destination_type: e.target.elements.destination_type.value,
      page_id: e.target.elements.page_id.value,
      instagram_id: e.target.elements.instagram_id.value,
      min_budget: e.target.elements.min_budget.value,
      opt_window: e.target.elements.opt_window.value,
      country: e.target.elements.country.value,
      ad_account: e.target.elements.ad_account.value,
    });
  };

  const configs = [
    general,
    recruitment_sample,
    recruitment_destination_experiment,
    recruitment_pipeline_experiment,
    destination,
    creative,
    targeting,
    targeting_distribution,
  ];

  const [index, setIndex] = useState(0);

  const config = configs[index];

  const isLast = index === configs.length - 1 ? true : false;

  const handleClick = () => {
    if (isLast) {
      return;
    }
    setIndex(prevCount => prevCount + 1);
  };

  const dynamicConfig = useMemo(() => {
    return getConfig(config);
  }, [config]);

  const configLabel = createLabelFor(config.configType);
  const configDescription = config.description;

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0">
          <h3 className="text-lg font-medium leading-6 text-gray-900">
            {configLabel}
          </h3>
          <p className="mt-1 text-sm text-gray-600">{configDescription}</p>
        </div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmitForm}>
          <div className="shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 bg-white sm:p-6">
              <div className="grid grid-cols-6 gap-6">
                <div className="col-span-6 sm:col-span-4">
                  <Renderer
                    config={dynamicConfig}
                    erroroncreate={errorOnCreate}
                    state={state}
                    setstate={wrapperSetState}
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
  );
};

export default NewStudyPage;
