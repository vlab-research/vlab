import React, { useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { useQueryClient } from 'react-query';
import SubmitButton from '../../components/SubmitButton';
import Variable, { ExtractionError } from './Variable';
import { TemplateCampaignContext, TemplateCampaignWrapper } from '../../components/TemplateCampaignWrapper'
import useAdsets from '../../hooks/useAdsets';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import ConfWrapper from '../../components/ConfWrapper';
import LoadingPage from '../../../../components/LoadingPage';
import {
  Variable as VariableType,
  GlobalFormData,
  Level as LevelType,
} from '../../../../types/conf';
import { Account } from '../../../../types/account';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { GenericListFactory } from '../../components/GenericList';
import { extractFromAdset, AdsetNotFoundError, PropertyMissingError } from './extract';

const VariableList = GenericListFactory<VariableType>();

interface Props {
  account: any;
  id: string;
  localData: VariableType[];
  globalData: GlobalFormData;
  facebookAccount: Account;
}

const isLevelStale = (level: LevelType, properties: string[]): boolean => {
  const hasTargeting =
    level.facebook_targeting && Object.keys(level.facebook_targeting).length > 0;
  const adsetStale = level.template_adset !== level.lastExtractedAdset;
  const propertiesStale =
    JSON.stringify(properties || []) !==
    JSON.stringify(level.lastExtractedProperties || []);
  return !hasTargeting || adsetStale || propertiesStale;
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

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [levelErrors, setLevelErrors] = useState<Map<string, ExtractionError | null>>(
    new Map()
  );

  const credentials: any = facebookAccount.connectedAccount?.credentials
  const accessToken = credentials?.access_token;

  const templateCampaign = useContext(TemplateCampaignContext)

  const { adsets, query: adsetsQuery } = useAdsets(templateCampaign!, accessToken);
  const queryClient = useQueryClient();

  const hasEmptyTargeting = formData.some(variable =>
    variable.levels.some(level => !level.facebook_targeting || Object.keys(level.facebook_targeting).length === 0)
  );

  const staleLevelCount = formData.reduce(
    (acc, variable) =>
      acc + variable.levels.filter(l => isLevelStale(l, variable.properties)).length,
    0
  );

  const canSubmit = !hasEmptyTargeting;

  const handleRefreshFromMeta = async () => {
    setIsRefreshing(true);
    const newLevelErrors = new Map<string, ExtractionError | null>();
    try {
      const adsetsQueryKey = `adsets${templateCampaign}${accessToken}`;
      await queryClient.invalidateQueries(adsetsQueryKey);
      await queryClient.refetchQueries(adsetsQueryKey);

      const cachedData = queryClient.getQueryData(adsetsQueryKey) as any;
      const freshAdsets: any[] = (cachedData?.pages || []).flatMap(
        (p: any) => p.data
      );

      const updatedData = formData.map((variable, vIdx) => ({
        ...variable,
        levels: variable.levels.map((level, lIdx) => {
          const key = `${vIdx}:${lIdx}`;
          if (!level.template_adset) {
            newLevelErrors.set(key, null);
            return { ...level, facebook_targeting: {} };
          }
          const adset = freshAdsets.find(a => a.id === level.template_adset);
          try {
            const extracted = extractFromAdset(adset, variable.properties);
            newLevelErrors.set(key, null);
            return {
              ...level,
              facebook_targeting: extracted,
              lastExtractedTime: Date.now(),
              lastExtractedAdset: level.template_adset,
              lastExtractedProperties: [...variable.properties],
            };
          } catch (err) {
            if (err instanceof AdsetNotFoundError) {
              newLevelErrors.set(key, {
                kind: 'adset_not_found',
                adsetName: err.adsetName,
              });
            } else if (err instanceof PropertyMissingError) {
              newLevelErrors.set(key, {
                kind: 'property_missing',
                adsetName: err.adsetName,
                propertyKey: err.propertyKey,
              });
            } else {
              newLevelErrors.set(key, {
                kind: 'adset_not_found',
                adsetName: level.template_adset,
              });
            }
            return { ...level, facebook_targeting: {} };
          }
        }),
      }));
      setFormData(updatedData);
      setLevelErrors(newLevelErrors);
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
        <div className="mb-4 flex items-center gap-3 flex-wrap">
          <button
            type="button"
            onClick={handleRefreshFromMeta}
            disabled={isRefreshing}
            data-testid="refresh-from-meta-button"
            className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh from Meta'}
          </button>
          <div data-testid="form-staleness-summary" className="text-sm">
            {staleLevelCount > 0 ? (
              <span className="text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded">
                {staleLevelCount} {staleLevelCount === 1 ? 'level needs' : 'levels need'} refresh
              </span>
            ) : (
              <span className="text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded">
                All levels up to date
              </span>
            )}
          </div>
        </div>

        <VariableList
          Element={Variable}
          elementName="variable"
          elementProps={{
            campaignId: templateCampaign,
            adsets: adsets,
            levelErrors,
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
          {!hasEmptyTargeting && staleLevelCount > 0 && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded">
              {staleLevelCount} {staleLevelCount === 1 ? 'level has' : 'levels have'} outdated targeting — consider clicking Refresh from Meta before submitting.
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
