import React from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import { GlobalFormData, CreateStudy as StudyType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { Account } from '../../../../types/account';
import useOptimize from '../../hooks/useOptimize';

interface Props {
  id: string;
  globalData: GlobalFormData;
  study: StudyType;
  facebookAccount: Account;
}

const Optimize: React.FC<Props> = ({ id, globalData, study, facebookAccount }: Props) => {
  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;

  const { optimize, isLoading } = useOptimize()

  const onClick = (): void => {

    optimize({ studySlug })

  };

  // TODO: add checks for valid studyconf, make sure everything is good.
  // and/or just do that on the backend, which it already does...

  return (
    <ConfWrapper>
      <p>
        Dont do this unless youre Nandan. At least not for now.
      </p>

      <PrimaryButton onClick={onClick} loading={isLoading}> Optimize </PrimaryButton>
    </ConfWrapper>
  );
};

export default Optimize;
