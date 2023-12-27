import React, { useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import Variable from './Variable';
import { TemplateCampaignContext, TemplateCampaignWrapper } from '../../components/TemplateCampaignWrapper'
import useAdsets from '../../hooks/useAdsets';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import ConfWrapper from '../../components/ConfWrapper';
import LoadingPage from '../../../../components/LoadingPage';
import {
  Variable as VariableType,
  GlobalFormData,
} from '../../../../types/conf';
import { Account } from '../../../../types/account';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';


interface Props {
  account: any;
  id: string;
  localData: VariableType[];
  globalData: GlobalFormData;
  facebookAccount: Account;
}

const Variables: React.FC<Props> = ({
  facebookAccount,
  id,
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

  const { createStudyConf } = useCreateStudyConf(
    'Variables saved',
    studySlug,
    'variables'
  );

  const [formData, setFormData] = useState<any[]>(
    localData ? localData : initialState
  );

  const credentials: any = facebookAccount.connectedAccount?.credentials
  const accessToken = credentials?.access_token;

  const templateCampaign = useContext(TemplateCampaignContext)

  const { adsets, query: adsetsQuery } = useAdsets(templateCampaign!, accessToken);

  if (adsetsQuery.isLoading) {
    return (
      <LoadingPage text="(loading ad sets from template campaign)" />
    );
  }

  if (adsetsQuery.isError) {
    return (
      <ErrorPlaceholder
        message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
        onClickTryAgain={() => window.location.reload()}
      />
    );
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
    <div className="mb-8">

      <form onSubmit={onSubmit}>
        {formData.map((d: any, index: number) => {
          return (
            <div key={index}>
              <Variable
                adsets={adsets}
                key={index}
                data={d}
                campaignId={templateCampaign!}
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

        <div className="p-6 text-right">
          <PrimaryButton type="submit" testId="form-submit-button">
            Next
          </PrimaryButton>

        </div>
      </form>
    </div>
  );
};



const VariablesWrapper: React.FC<Props> = props => {
  const existingCampaign = props.localData && props.localData[0]?.levels[0]?.template_campaign;

  return (
    <ConfWrapper>
      <TemplateCampaignWrapper
        globalData={props.globalData}
        facebookAccount={props.facebookAccount}
        existingCampaign={existingCampaign}
      >
        <Variables {...props} />
      </TemplateCampaignWrapper>
    </ConfWrapper>
  )
}

export default VariablesWrapper;
