import React, { useState } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import { GenericSelect, SelectI } from '../../components/Select';
import SubmitButton from '../../components/SubmitButton';
import PrimaryButton from '../../../../components/PrimaryButton';
import { GlobalFormData, CopyFromConf as FormData, CreateStudy as StudyType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { Account } from '../../../../types/account';
import useStudies from '../../../StudiesPage/hooks/useStudies';
import useCopyConfs from '../../hooks/useCopyConfs';
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  id: string;
  globalData: GlobalFormData;
  study: StudyType;
  facebookAccount: Account;
}

const Initialize: React.FC<Props> = ({ id, globalData, study, facebookAccount }: Props) => {
  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;
  const initialState = {
    source_study_slug: '',
  };

  const history = useHistory();
  const [formData, setFormData] = useState<FormData>(initialState);

  const { copyConfs, isLoading } = useCopyConfs("All confs except general have been copied", studySlug);

  const { studies } = useStudies();

  const onSubmit = (e: any): void => {
    e.preventDefault();
    history.push(`/studies/${studySlug}/general`);
  };

  const onClickCopy = (): void => {
    copyConfs({ data: formData, studySlug })
  }

  const studyOptions = [
    { name: '', label: 'Select an existing study to copy initial values' },
    ...studies.map(s => ({ name: s.slug, label: s.name }))
  ]

  const handleChange = (e: any): void => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value })
  }

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <p>
          You can initialize your study from the configuration of an existing study by selecting it here. Please note: if you have made any changes to this new study, they will be overwritten by clicking "Initialize Values." If you wish to start from scratch, just click next.
        </p>

        <Select
          name="source_study_slug"
          handleChange={handleChange}
          options={studyOptions}
          value={formData.source_study_slug}
          required={false}
        />
        <PrimaryButton
          type="button"
          leftIcon="RefreshIcon"
          onClick={onClickCopy}
        >
          Initialize Values
        </PrimaryButton>

        <SubmitButton isLoading={isLoading} />
      </form>
    </ConfWrapper>
  );
};

export default Initialize;
