import React, { useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import useAds from '../../hooks/useAds';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import { Account } from '../../../../types/account';
import Creative from './Creative';
import LoadingPage from '../../../../components/LoadingPage';
import {
  Creatives as CreativesType,
  GlobalFormData,
} from '../../../../types/conf';
import { Creative as CreativeType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { TemplateCampaignContext, TemplateCampaignWrapper } from '../../components/TemplateCampaignWrapper'
import { GenericListFactory } from '../../components/GenericList';

const CreativeList = GenericListFactory<CreativeType>();

interface Props {
  id: string;
  localData: CreativesType;
  globalData: GlobalFormData;
  facebookAccount: Account;
}

const Creatives: React.FC<Props> = ({
  id,
  localData,
  globalData,
  facebookAccount,
}: Props) => {
  const destinations = globalData.destinations && globalData.destinations;
  const templateCampaign = useContext(TemplateCampaignContext)

  const initialState = [
    {
      name: '',
      destination: globalData.destinations && globalData.destinations[0].name,
      template: '',
      template_campaign: templateCampaign || '',
    },
  ];

  const [formData, setFormData] = useState<CreativeType[]>(
    localData ? localData : initialState
  );

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Creatives saved',
    studySlug,
    'creatives'
  );

  const credentials: any = facebookAccount.connectedAccount?.credentials
  const accessToken = credentials?.access_token;

  const { ads, query: adsQuery } = useAds(templateCampaign!, accessToken);

  if (adsQuery.isLoading) {
    return (
      <LoadingPage text="(loading ad account information)" />
    );
  }

  if (adsQuery.isError) {
    return (
      <ErrorPlaceholder
        showImage={false}
        message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
        onClickTryAgain={() => window.location.reload()}
      />
    );
  }


  if (ads.length === 0) {
    return (
      <ErrorPlaceholder
        showImage={true}
        message={`Sorry, the select campaign ${templateCampaign}, does not seem to have any ads for us to use as template creatives. Make sure you published the ads and selected the correct campaign.`}
        onClickTryAgain={adsQuery.refetch}
      />
    );
  }

  const onSubmit = (e: any): void => {
    e.preventDefault();
    createStudyConf({ data: formData, studySlug, confType: id });
  };


  return (
    <form onSubmit={onSubmit}>
      <CreativeList
        Element={Creative}
        elementName="creative"
        elementProps={{ ads: ads, destinations: destinations, studySlug: studySlug }}
        data={formData}
        setData={setFormData}
        initialState={initialState}
      />
      <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
    </form>
  );
};


const CreativesWrapper: React.FC<Props> = props => {
  const existingCampaign = props.localData && props.localData[0]?.template_campaign;

  return (
    <ConfWrapper>
      <TemplateCampaignWrapper
        globalData={props.globalData}
        facebookAccount={props.facebookAccount}
        existingCampaign={existingCampaign}
      >
        <Creatives {...props} />
      </TemplateCampaignWrapper>
    </ConfWrapper>
  )
}


export default CreativesWrapper;
