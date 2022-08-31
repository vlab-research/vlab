import React from 'react';
import { ExclamationCircleIcon } from '@heroicons/react/solid';
import useCreateStudy from './useCreateStudy';
import PageLayout from '../../components/PageLayout';
import PrimaryButton from '../../components/PrimaryButton';
import { classNames } from '../../helpers/strings';

const NewStudyPage = () => (
  <PageLayout title={'New Study'} testId="new-study-page" showBackButton>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const { isCreating, errorMessage, createStudy } = useCreateStudy();

  const handleSubmitForm = (event: any) => {
    event.preventDefault();

    createStudy({ name: event.target.elements.name.value });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0">
          <h3 className="text-lg font-medium leading-6 text-gray-900">
            General Information
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Fill general information about the Study.
          </p>
        </div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmitForm}>
          <div className="shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 bg-white sm:p-6">
              <div className="grid grid-cols-6 gap-6">
                <div className="col-span-6 sm:col-span-4">
                  <NameInput errorMessage={errorMessage} />
                </div>
              </div>
            </div>
            <div className="px-4 py-3 bg-gray-50 text-right sm:px-6">
              <PrimaryButton
                type="submit"
                loading={isCreating}
                testId="new-study-submit-button"
              >
                Create
              </PrimaryButton>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

const NameInput = ({ errorMessage }: { errorMessage?: string }) => (
  <React.Fragment>
    <label htmlFor="name" className="block text-sm font-medium text-gray-700">
      Name
    </label>
    <div className="relative">
      <input
        type="text"
        name="name"
        id="name"
        className={classNames(
          'mt-1 block w-full shadow-sm sm:text-sm rounded-md',
          errorMessage
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
        data-testid="new-study-name-input"
      />
      {errorMessage && (
        <div className="absolute pointer-events-none inset-y-0 right-0 pr-3 flex items-center">
          <ExclamationCircleIcon
            className="h-5 w-5 text-red-500"
            aria-hidden="true"
          />
        </div>
      )}
    </div>

    <p className="mt-2 text-sm text-red-600 h-1">{errorMessage}</p>
  </React.Fragment>
);

export default NewStudyPage;
