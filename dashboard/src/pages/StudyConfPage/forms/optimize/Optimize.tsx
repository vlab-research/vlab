import React from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import { GlobalFormData, CreateStudy as StudyType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { Account } from '../../../../types/account';
import useOptimize from '../../hooks/useOptimize';
import Instruction from './Instruction';

interface Props {
  id: string;
  globalData: GlobalFormData;
  study: StudyType;
  facebookAccount: Account;
}

const Optimize: React.FC<Props> = ({ id, globalData, study, facebookAccount }: Props) => {
  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;

  const { optimize, isLoading: isOptimizing, data: instructions } = useOptimize()

  const onClick = (): void => {
    optimize({ studySlug })
  };

  // TODO: add checks for valid studyconf, make sure everything is good.
  // and/or just do that on the backend, which it already does...

  return (
    <ConfWrapper>
      <PrimaryButton onClick={onClick} loading={isOptimizing}> Optimize </PrimaryButton>

      {instructions ?
        <p className="py-6 text-sm/6 text-gray-900"> Given the current state of your campaigns on Facebook, please run the following instructions in order to optimize this study: </p>
        : null}


      {instructions?.data.map((instruction: any, i: number) => {
        return (
          <Instruction instruction={instruction} key={i} studySlug={studySlug} />
        )
      }

      )}
    </ConfWrapper>
  );
};

export default Optimize;
