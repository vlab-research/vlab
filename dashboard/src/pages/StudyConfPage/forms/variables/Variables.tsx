import React, { useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import SubmitButton from '../../components/SubmitButton';
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
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { GenericListFactory } from '../../components/GenericList';

const VariableList = GenericListFactory<VariableType>();

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

  const { isLoadingOnCreateStudyConf, createStudyConf } = useCreateStudyConf(
    'Variables saved',
    studySlug,
    'variables'
  );

  const [formData, setFormData] = useState<VariableType[]>(
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

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const formatted = formData.map(v => ({
      ...v,
      levels: v.levels.map((l: any) => ({ ...l, quota: +l.quota })),
    }));

    createStudyConf({ data: formatted, studySlug, confType: id });
  };


  return (
    <div className="mb-8">
      <form onSubmit={onSubmit}>
        <VariableList
          Element={Variable}
          elementName="variable"
          elementProps={{ campaignId: templateCampaign, adsets: adsets }}
          data={formData}
          setData={setFormData}
          initialState={initialState}
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
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
