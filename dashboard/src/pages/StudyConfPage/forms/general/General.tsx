import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import PrimaryButton from '../../../../components/PrimaryButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { General as FormData, CreateStudy as StudyType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  id: string;
  localData: FormData;
  study: StudyType;
  confKeys: string[];
}

const General: React.FC<Props> = ({ id, localData, study, confKeys }: Props) => {
  const initialState = {
    name: study.name,
    credentials_key: '',
    credentials_entity: '',
    ad_account: '',
    opt_window: 0,
  };

  const [formData, setFormData] = useState<FormData>(initialState);

  useEffect(() => {
    localData && setFormData(localData);
  }, [localData]);


  // TODO: clean up this nonsense.
  useEffect(() => {
    if (localData) {
      return setFormData({ ...localData, name: study.name });
    }
    setFormData({ ...initialState, name: study.name });

  }, [study]);

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'General settings saved',
    studySlug,
    confKeys,
    'general'
  );

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

  // get all credentials to get entity and key...

  // or do on initial page?

  // no reason it shouldn't be in general, really... all though it's higher level in a sense?

  // Or should it have its own conf? AccountConf --> with creds, ad account, etc.?
  // Page can come from creative, as can instagram ID, no more need for it.

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <TextInput
          name="name"
          handleChange={handleChange}
          placeholder="E.g My Survey"
          value={formData.name}
        />
        <TextInput
          name="ad_account"
          handleChange={handleChange}
          placeholder="E.g 1342820622846299"
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
