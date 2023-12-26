import React, { useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
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

interface Props {
  id: string;
  localData: CreativesType;
  globalData: GlobalFormData;
  facebookAccount: Account;
  confKeys: string[];
}

const Creatives: React.FC<Props> = ({
  id,
  localData,
  globalData,
  facebookAccount,
  confKeys,
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
    confKeys,
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
        message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
        onClickTryAgain={() => window.location.reload()}
      />
    );
  }

  const onSubmit = (e: any): void => {
    e.preventDefault();
    createStudyConf({ data: formData, studySlug, confType: id });
  };

  const addCreative = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteCreative = (i: number): void => {
    const newArr = formData.filter((_: CreativeType, ii: number) => ii !== i);

    setFormData(newArr);
  };

  const updateFormData = (c: CreativeType, index: number): void => {
    const clone = [...formData];
    clone[index] = c;
    setFormData(clone);
  };

  return (
    <form onSubmit={onSubmit}>
      <div className="mb-8">
        {formData.map((d: CreativeType, index: number) => {
          return (
            <ul key={index}>
              <Creative
                ads={ads}
                data={d}
                index={index}
                destinations={destinations}
                updateFormData={updateFormData}
                studySlug={studySlug}
              />
              {formData.length > 1 && (
                <div key={`${d.name}-${index}`}>
                  <div className="flex flex-row w-4/5 justify-between items-center">
                    <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                    <DeleteButton
                      onClick={() => deleteCreative(index)}
                    ></DeleteButton>
                  </div>
                  <div />
                </div>
              )}
            </ul>
          );
        })}
        <AddButton onClick={addCreative} label="Add creative" />
      </div>

      <div className="p-6 text-right">
        <PrimaryButton
          leftIcon="CheckCircleIcon"
          type="submit"
          testId="form-submit-button"
          loading={isLoadingOnCreateStudyConf}
        >
          Next
        </PrimaryButton>
      </div>
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
