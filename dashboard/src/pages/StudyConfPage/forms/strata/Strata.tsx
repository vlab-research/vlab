import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import Variable from './Variable';
import { createLabelFor } from '../../../../helpers/strings';
import useAccounts from './useAccounts';
import useCampaigns from './useCampaigns';
import useAdsets from './useAdsets';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';

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

const Select: React.FC<SelectProps> = ({ options, value, onChange }: SelectProps) => {

  const onSelect = (e: any) => {
    onChange(e.target.value)
  }

  return (
    <div className="sm:my-4" >
      <label className="my-2 block text-sm font-medium text-gray-700">
        Pick a campaign template
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
    </div >
  )
};

interface Props {
  account: any;
  id: string;
  localData: any;
  globalData: any;
}

const Strata: React.FC<Props> = ({ account, id, globalData, localData }: Props) => {
  const initialState = [
    {
      name: '',
      id: '',
      properties: [],
      levels: []
    },
  ];

  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;

  const { createStudyConf } = useCreateStudyConf(
    true,
    'Study settings saved'
  );

  const [formData, setFormData] = useState<any[]>(
    localData ? localData : initialState
  );

  console.log('FormData: ', formData)

  const [templateCampaign, setTemplateCampaign] = useState<string>();

  const accessToken = account?.connectedAccount.credentials.access_token
  const adAccount = globalData.general?.ad_account

  const { query: campaignQuery, campaigns } = useCampaigns(adAccount, accessToken);

  // TODO:
  // store template campaign? Hm. Probably...
  useEffect(() => {
    campaigns.length > 0 && setTemplateCampaign(campaigns[0].id)
  }, [campaigns.length > 0 && campaigns[0].id])

  const { query: adsetsQuery, adsets } = useAdsets(adAccount, templateCampaign!, accessToken);

  if (campaignQuery.isLoading) {
    return null // spinner
    // Something with adsetsQuery isLoading or error?
  }

  const updateFormData = (d: any, index: number): void => {
    const clone = [...formData];
    clone[index] = d;
    setFormData(clone);
  };

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const creatives = globalData.creatives
      ? globalData.creatives.map((c: any) => c.name)
      : [];

    const d = formData
      .flatMap((x: any) => x.levels.map((y: any) => ({ ...y, id: `${x.name}-${y.name}` })))
      .map(data => (
        {
          audiences: [],
          excluded_audiences: [],
          metadata: {},
          creatives: creatives,

          ...data,
          quota: +data.quota, // TODO: cast to number earlier in the process
        }))
      .map(d => {
        delete d.name
        // delete d.adset_id
        return d
      })


    console.log('Submit Data: ', d)

    createStudyConf({ data: d, studySlug })
  };

  const addVariable = (): void => {
    setFormData([...formData, ...initialState]);
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
                    <Variable
                      adsets={adsets}
                      key={index}
                      data={d}
                      formData={formData}
                      index={index}
                      updateFormData={updateFormData}
                    />
                  );
                })}

                <div className="w-4/5 h-0.5 mr-8 my-6 rounded-md bg-gray-400"></div>
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

const StrataWrapper: React.FC<Props> = (props) => {
  const { query, account, errorMessage } = useAccounts();

  if (query.isLoading) {
    return null // spinner
  }

  // if not account, show an error message and a button to
  // connect an account

  // if there is an account, continue

  return (
    <Strata {...props} account={account} />
  )
}

export default StrataWrapper;
