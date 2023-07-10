import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import Variable from './Variable';
import { createLabelFor } from '../../../../helpers/strings';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import useFacebookAccounts from './useFacebookAccounts';
import useCampaigns from './useCampaigns';
import useAdsets from './useAdsets';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import {
  Variable as VariableType,
  GlobalFormData,
} from '../../../../types/conf';
import DeleteButton from '../../../../components/DeleteButton';

interface SelectProps {
  name: string;
  options: SelectOption[];
  onChange: any;
  value?: string;
}

interface SelectOption {
  name: string;
  id: string;
}

const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
}: SelectProps) => {
  const onSelect = (e: any) => {
    onChange(e.target.value);
  };

  return (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        Pick a template campaign
      </label>
      <select
        className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
        onChange={onSelect}
        value={value}
      >
        {options.map((option: SelectOption, i: number) => (
          <option key={i} value={option.id}>
            {createLabelFor(option.name)}
          </option>
        ))}
      </select>
    </div>
  );
};

interface Props {
  account: any;
  id: string;
  localData: VariableType[];
  globalData: GlobalFormData;
}

const Variables: React.FC<Props> = ({
  account,
  id,
  globalData,
  localData,
}: Props) => {
  const initialState: VariableType[] = [
    {
      name: '',
      properties: [],
      levels: [],
    },
  ];

  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;

  const { createStudyConf } = useCreateStudyConf(true, 'Study settings saved');

  const [formData, setFormData] = useState<any[]>(
    localData ? localData : initialState
  );

  console.log('FormData: ', formData);

  const accessToken = account?.connectedAccount.credentials.access_token;
  const adAccount = globalData.general?.ad_account;

  const { campaigns, loadingCampaigns, errorLoadingCampaigns, refetchData } =
    useCampaigns(adAccount, accessToken);

  // TODO:
  // store template campaign? Hm. Probably...

  const tc = localData
    ? localData[0].levels[0]?.template_campaign
    : campaigns[0]?.id;
  const [templateCampaign, setTemplateCampaign] = useState<string>(tc);

  const { adsets } = useAdsets(templateCampaign!, accessToken);

  if (errorLoadingCampaigns) {
    return (
      <ErrorPlaceholder
        message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
        onClickTryAgain={refetchData}
      />
    );
  }

  if (loadingCampaigns) {
    return (
      <h1 className="text-3xl font-bold leading-tight text-gray-900 flex-1">
        Loading...{' '}
      </h1>
    );
    // Something with adsetsQuery isLoading or error?
  }

  const updateFormData = (d: any, index: number): void => {
    const clone = [...formData];
    clone[index] = d;
    setFormData(clone);
  };

  const onSubmit = (e: any): void => {
    e.preventDefault();

    console.log('submit formData', formData);
    const formatted = formData.map(v => ({
      ...v,
      levels: v.levels.map((l: any) => ({ ...l, quota: +l.quota })),
    }));

    console.log('formatted', formatted);
    const data = { [id]: formatted };
    createStudyConf({ data, studySlug });
  };

  const addVariable = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteVariable = (i: number): void => {
    const newArr = localData.filter((_: any, ii: number) => ii !== i);
    setFormData(newArr);
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <form onSubmit={onSubmit}>
              <div className="mb-8">
                <Select
                  name="campaign"
                  options={campaigns}
                  onChange={setTemplateCampaign}
                  value={templateCampaign}
                ></Select>
                {formData.map((d: any, index: number) => {
                  return (
                    <>
                      <Variable
                        adsets={adsets}
                        key={index}
                        data={d}
                        formData={formData}
                        campaignId={templateCampaign}
                        index={index}
                        updateFormData={updateFormData}
                      />
                      <div>
                        <div className="flex flex-row w-4/5 justify-between items-center">
                          <div className="w-4/5 h-0.5 mr-8 my-4 rounded-md bg-gray-400"></div>
                          <DeleteButton
                            onClick={() => deleteVariable(index)}
                          ></DeleteButton>
                        </div>
                        <div />
                      </div>
                    </>
                  );
                })}
                <div className="flex flex-row items-center">
                  <AddButton onClick={addVariable} />
                  <label className="ml-4 italic text-gray-700 text-sm">
                    Add a new variable
                  </label>
                </div>
              </div>

              <div className="p-6 text-right">
                <PrimaryButton type="submit" testId="form-submit-button">
                  Save
                </PrimaryButton>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

const VariablesWrapper: React.FC<Props> = props => {
  const { account, accountsLoading, errorLoadingAccounts, refetchData } =
    useFacebookAccounts();

  if (errorLoadingAccounts) {
    return (
      <ErrorPlaceholder
        message="Something went wrong while fetching your account."
        onClickTryAgain={refetchData}
      />
      // TODO add connect button
    );
  }

  if (accountsLoading) {
    return (
      <h1 className="text-3xl font-bold leading-tight text-gray-900 flex-1">
        Loading Facebook account...
      </h1>
    );
  }

  return <Variables {...props} account={account} />;
};

export default VariablesWrapper;
