import React, { useState } from 'react';
import {
  GlobalFormData,
} from '../../../types/conf';
import { createContext } from 'react';
import { GenericSelect, SelectI } from '../components/Select';
import { Account } from '../../../types/account';
import useCampaigns from '../hooks/useCampaigns';
import LoadingPage from '../../../components/LoadingPage';
import ErrorPlaceholder from '../../../components/ErrorPlaceholder';

export const TemplateCampaignContext = createContext<string | undefined>(undefined);

interface Props {
  globalData: GlobalFormData;
  existingCampaign: string | undefined;
  facebookAccount: Account;
  children: React.ReactNode;
}

export const TemplateCampaignWrapper: React.FC<Props> = ({
  facebookAccount,
  globalData,
  existingCampaign,
  children,
}: Props) => {


  const credentials: any = facebookAccount.connectedAccount?.credentials
  const accessToken = credentials?.access_token;

  const adAccount = globalData && globalData.general?.ad_account

  const { campaigns, query: campaignsQuery } =
    useCampaigns(adAccount, accessToken);

  const [templateCampaign, setTemplateCampaign] = useState<string>(existingCampaign || "");

  if (campaignsQuery.isLoading) {
    return (
      <LoadingPage text="(loading ad account information)" />
    );
  }


  if (!adAccount) {
    return (
      <ErrorPlaceholder
        message='It seems that you have not selected an Ad Account to use for this study. Please go to the General tab, select an Ad Account, and submit the information. If the error persists, please contact your administrator.'
        onClickTryAgain={() => window.location.reload()}
      />
    )
  }


  if (campaignsQuery.isError) {
    return (
      <ErrorPlaceholder
        message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
        onClickTryAgain={() => window.location.reload()}
      />
    )
  }

  const campaignOptions = [
    { name: '', label: 'Please choose an option' },
    ...campaigns.map(c => ({ name: c.id, label: c.name }))
  ]

  const Select = GenericSelect as SelectI<{ template_campaign: string }>;

  const handleChange = (e: any) => {
    setTemplateCampaign(e.target.value)
  }

  return (
    <TemplateCampaignContext.Provider value={templateCampaign}>
      <div className="mb-8">
        <Select
          name="template_campaign"
          options={campaignOptions}
          handleChange={handleChange}
          value={templateCampaign}
        ></Select>
        <div className="flex w-full h-0.5 mr-4 my-10 rounded-md bg-gray-400"></div>

        {templateCampaign ?

          children :
          <p> Please pick a campaign first </p>
        }



      </div>
    </TemplateCampaignContext.Provider>
  )
}
