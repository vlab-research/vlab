import React, { useState, useContext, useMemo } from 'react';
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
import { extractFromAdset, isLevelInSync } from './extract';

const VariableList = GenericListFactory<VariableType>();

interface Props {
  account: any;
  id: string;
  localData: VariableType[];
  globalData: GlobalFormData;
  facebookAccount: Account;
}

const formatRelativeTime = (timestamp: number): string => {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

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
  const queryClient = useQueryClient();

  const metaAvailable = (adsets?.length ?? 0) > 0;
  const metaIsLoading = !metaAvailable || adsetsQuery.isFetching;
  const metaIsRefreshing = adsetsQuery.isFetching;
  const metaIsError = adsetsQuery.isError && !metaAvailable;
  const metaLastPulledAt: number | null = adsetsQuery.dataUpdatedAt ?? null;

  const handleRefreshFromMeta = async () => {
    const adsetsQueryKey = `adsets${templateCampaign}${accessToken}`;
    await queryClient.invalidateQueries(adsetsQueryKey);
    await queryClient.refetchQueries(adsetsQueryKey);
  };

  const hasEmptyTargeting = formData.some(variable =>
    variable.levels.some(level =>
      !level.facebook_targeting || Object.keys(level.facebook_targeting).length === 0
    )
  );

  const outOfSyncCount = useMemo(() => {
    if (!metaAvailable) return 0;
    return formData.reduce((acc, variable) =>
      acc + variable.levels.filter(level => {
        try {
          const adset = adsets.find((a: any) => a.id === level.template_adset);
          const wouldApply = extractFromAdset(adset, variable.properties);
          return !isLevelInSync(level.facebook_targeting, wouldApply);
        } catch {
          return true;
        }
      }).length, 0);
  }, [formData, adsets, metaAvailable]);

  const canSubmit = !hasEmptyTargeting;

  if (metaIsLoading) {
    return (
      <LoadingPage text="(loading ad sets from template campaign)" />
    );
  }

  if (metaIsError) {
    return (
      <ErrorPlaceholder
        message='Something went wrong while fetching your campaigns. Have you connected a Facebook account under "Connected Accounts"?'
        onClickTryAgain={() => window.location.reload()}
      />
    );
  }

  const onSubmit = (e: any): void => {
    e.preventDefault();

    if (!canSubmit) return;

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
        <div className="mb-4 flex items-center gap-3 flex-wrap">
          <button
            type="button"
            onClick={handleRefreshFromMeta}
            disabled={metaIsRefreshing}
            data-testid="refresh-from-meta-button"
            className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:bg-gray-400"
          >
            {metaIsRefreshing ? 'Refreshing from Meta…' : 'Refresh from Meta'}
          </button>
          {metaIsRefreshing && (
            <span className="text-sm text-gray-500">Loading…</span>
          )}
          {!metaIsRefreshing && metaLastPulledAt && (
            <span className="text-sm text-gray-500" data-testid="meta-last-pulled">
              Meta last pulled: {formatRelativeTime(metaLastPulledAt)}
            </span>
          )}
          {!metaIsRefreshing && adsetsQuery.isError && (
            <span className="text-sm text-red-700" data-testid="meta-pull-error">
              Pull failed — click to retry.
            </span>
          )}
        </div>

        <VariableList
          Element={Variable}
          elementName="variable"
          elementProps={{
            campaignId: templateCampaign,
            adsets: adsets,
            metaIsLoading,
            metaIsError,
          }}
          data={formData}
          setData={setFormData}
          initialState={initialState}
        />

        <div className="mt-6 space-y-2">
          {hasEmptyTargeting && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded">
              All levels must have extracted targeting data before submitting.
            </div>
          )}
          {!hasEmptyTargeting && outOfSyncCount > 0 && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded">
              {outOfSyncCount} {outOfSyncCount === 1 ? 'level is' : 'levels are'} out of sync with current Meta data — Apply on the variable above each to sync before submitting.
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
