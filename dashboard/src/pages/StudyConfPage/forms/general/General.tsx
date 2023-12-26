import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import PrimaryButton from '../../../../components/PrimaryButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { General as FormData, CreateStudy as StudyType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { Account } from '../../../../types/account';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import useAdAccounts from '../../hooks/useAdAccounts';
import LoadingPage from '../../../../components/LoadingPage';
const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  id: string;
  localData: FormData;
  study: StudyType;
  facebookAccount: Account;
  confKeys: string[];
}

const General: React.FC<Props> = ({ id, localData, study, confKeys, facebookAccount }: Props) => {
  const initialState = {
    name: study.name,
    credentials_key: 'Facebook', // hardcoded in API right now
    credentials_entity: 'facebook', // hardcoded in API right now
    ad_account: '',
    opt_window: 48,
  };

  const [formData, setFormData] = useState<FormData>(initialState);

  useEffect(() => {
    localData && setFormData(localData);
  }, [localData]);

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'General settings saved',
    studySlug,
    confKeys,
    'general'
  );

  const credentials: any = facebookAccount.connectedAccount?.credentials
  const accessToken = credentials?.access_token;
  const { adAccounts, query } = useAdAccounts(accessToken)

  if (query.isLoading) {
    return (
      <ConfWrapper>
        <LoadingPage text="(loading ad account information)" />
      </ConfWrapper>
    )
  }

  if (!adAccounts) {
    return (
      <ConfWrapper>
        <ErrorPlaceholder
          message='Something went wrong while fetching your Ad Accounts. Try again?'
          onClickTryAgain={query.refetch}
        />
      </ConfWrapper>
    )
  }


  const validateInput = (name: string, value: any) => {
    if (name === 'min_budget') {
      if (!value) {
        return parseFloat('0');
      }
      return parseFloat(value);
    }
    if (name === 'opt_window') {
      if (!value) {
        return parseInt('0');
      }
      return parseInt(value);
    }
    return value;
  };

  const updateFormData = (d: FormData): void => {
    setFormData(d);
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;

    updateFormData({ ...formData, [name]: validateInput(name, value) });
  };

  const onSubmit = (e: any): void => {
    e.preventDefault();
    const data = { ...formData, name: study.name }
    createStudyConf({ data, studySlug, confType: id });
  };

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <TextInput
          name="name"
          handleChange={handleChange}
          placeholder="E.g My Survey"
          value={formData.name}
        />
        <Select
          name="ad_account"
          handleChange={handleChange}
          options={adAccounts.map(a => ({ name: a.account_id, label: a.name }))}
          value={formData.ad_account}
        />
        <TextInput
          name="opt_window"
          handleChange={handleChange}
          placeholder="E.g 48"
          value={formData.opt_window}
        />

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
    </ConfWrapper>
  );
};

export default General;
