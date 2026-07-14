import React, { useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { useQueryClient } from 'react-query';
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
import { extractFromAdset } from './extract';

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

  const [isRefreshing, setIsRefreshing] = useState(false);

  const credentials: any = facebookAccount.connectedAccount?.credentials
  const accessToken = credentials?.access_token;

  const templateCampaign = useContext(TemplateCampaignContext)

  const { adsets, query: adsetsQuery } = useAdsets(templateCampaign!, accessToken);
  const queryClient = useQueryClient();


  // Check if Submit should be blocked: any level with empty targeting
  const hasEmptyTargeting = formData.some(variable =>
    variable.levels.some(level => !level.facebook_targeting || Object.keys(level.facebook_targeting).length === 0)
  );

  const canSubmit = !hasEmptyTargeting;

  // Refresh from Meta: refetch adsets and re-extract all levels
  const handleRefreshFromMeta = async () => {
    setIsRefreshing(true);
    try {
      const adsetsQueryKey = `adsets${templateCampaign}${accessToken}`;
      await queryClient.invalidateQueries(adsetsQueryKey);
      await queryClient.refetchQueries(adsetsQueryKey);

      // Re-extract for every level using its current template_adset and variable's properties
      const updatedData = formData.map(variable => ({
        ...variable,
        levels: variable.levels.map(level => {
          if (!level.template_adset) {
            return { ...level, facebook_targeting: {} };
          }
          const adset = adsets.find(a => a.id === level.template_adset);
          try {
            const extracted = extractFromAdset(adset, variable.properties);
            return { ...level, facebook_targeting: extracted };
          } catch (err) {
            // Errors will be surfaced on the level by the error state
            return { ...level, facebook_targeting: {} };
          }
        }),
      }));
      setFormData(updatedData);
    } finally {
      setIsRefreshing(false);
    }
  };

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

    // Gate submit on form state validity
    if (!canSubmit) {
      return;
    }

    const formatted = formData.map(v => ({
      ...v,
      name: v.name.trim(),
      levels: v.levels.map((l: any) => ({ ...l, quota: +l.quota, name: l.name.trim() })),
    }));

    createStudyConf({ data: formatted, studySlug, confType: id });
  };


  return (
    <div className="mb-8">
      <form onSubmit={onSubmit}>
        {/* Refresh from Meta button */}
        <div className="mb-4 flex gap-3">
          <button
            type="button"
            onClick={handleRefreshFromMeta}
            disabled={isRefreshing}
            className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh from Meta'}
          </button>
        </div>

        <VariableList
          Element={Variable}
          elementName="variable"
          elementProps={{
            campaignId: templateCampaign,
            adsets: adsets,
          }}
          data={formData}
          setData={setFormData}
          initialState={initialState}
        />

        {/* Submit button and hint */}
        <div className="mt-6 space-y-2">
          {!canSubmit && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded">
              All levels must have extracted targeting data before submitting.
            </div>
          )}
          <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
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
