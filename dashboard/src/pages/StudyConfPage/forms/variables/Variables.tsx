import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import Variable from './Variable';
import { createLabelFor } from '../../../../helpers/strings';
import useFacebookAccounts from './useFacebookAccounts';
import useCampaigns from './useCampaigns';
import useAdsets from './useAdsets';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import ConfWrapper from '../../components/ConfWrapper';
import {
  Variable as VariableType,
  GlobalFormData,
} from '../../../../types/conf';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';

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
  confKeys: string[];
}

const Variables: React.FC<Props> = ({
  account,
  id,
  globalData,
  localData,
  confKeys,
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

  const { createStudyConf } = useCreateStudyConf(
    'Variables saved',
    studySlug,
    confKeys,
    'variables'
  );

  const [formData, setFormData] = useState<any[]>(
    localData ? localData : initialState
  );

  const accessToken = account?.connectedAccount.credentials.access_token;
  const adAccount = globalData.general?.ad_account;

  const { campaigns, loadingCampaigns, errorLoadingCampaigns, refetchData } =
    useCampaigns(adAccount, accessToken);

  const tc = localData
    ? localData[0]?.levels[0]?.template_campaign
    : campaigns[0]?.id;

  const [templateCampaign, setTemplateCampaign] = useState<string>(tc);

  const { adsets } = useAdsets(templateCampaign!, accessToken);

  if (errorLoadingCampaigns) {
    return (
      <ConfWrapper>
        <ErrorPlaceholder
          message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
          onClickTryAgain={refetchData}
        />
      </ConfWrapper>
    );
  }

  if (loadingCampaigns) {
    return (
      <ConfWrapper>
        <h1 className="text-2xl leading-tight text-gray-900 flex-1">
          Loading Template Campaign...
        </h1>
      </ConfWrapper>
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

    const formatted = formData.map(v => ({
      ...v,
      levels: v.levels.map((l: any) => ({ ...l, quota: +l.quota })),
    }));

    createStudyConf({ data: formatted, studySlug, confType: id });
  };

  const addVariable = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteVariable = (i: number): void => {
    const newArr = formData.filter((_: any, ii: number) => ii !== i);
    setFormData(newArr);
  };

  return (
    <ConfWrapper>
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
              <div key={index}>
                <Variable
                  adsets={adsets}
                  key={index}
                  data={d}
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
              </div>
            );
          })}
          <div className="flex flex-row items-center">
            <AddButton onClick={addVariable} label="Add a variable" />
          </div>
        </div>

        <div className="p-6 text-right">
          <PrimaryButton type="submit" testId="form-submit-button">
            Next
          </PrimaryButton>
        </div>
      </form>
    </ConfWrapper>
  );
};

const VariablesWrapper: React.FC<Props> = props => {
  const { account, accountsLoading, errorLoadingAccounts, refetchData } =
    useFacebookAccounts();

  if (errorLoadingAccounts) {

    // TODO: add "connect" button

    return (
      <ConfWrapper>
        <ErrorPlaceholder
          message="Something went wrong while fetching your account."
          onClickTryAgain={refetchData}
        />
      </ConfWrapper>
    );
  }

  if (accountsLoading) {
    return (
      <ConfWrapper>
        <h1 className="text-3xl font-bold leading-tight text-gray-900 flex-1">
          Loading Facebook account...
        </h1>
      </ConfWrapper>
    );
  }

  return <Variables {...props} account={account} />;
};

export default VariablesWrapper;
