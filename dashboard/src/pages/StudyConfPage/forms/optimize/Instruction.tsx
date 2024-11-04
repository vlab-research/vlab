import React from 'react';
import SecondaryButton from '../../../../components/SecondaryButton';
import useRunInstruction from '../../hooks/useRunInstruction';

interface Props {
  instruction: any;
  studySlug: string;
}

const Instruction: React.FC<Props> = ({ instruction, studySlug }: Props) => {
  const { runInstruction, isLoading: isRunning, data: result, isError, error } = useRunInstruction()

  const onClick = (): void => {
    runInstruction({ studySlug, instruction })
  };

  return (
    <ul className="divide-y py-3 divide-gray-200">
      <li className="flex justify-between gap-x-6 py-5">
        <div className="flex gap-x-4">
          <div className="min-w-0 flex-auto">
            <p className="text-sm/6 font-semibold text-gray-900">{instruction.node}</p>
            <p className="mt-1 truncate text-xs/5 text-gray-500">{instruction.action}</p>
          </div>
        </div>
        <div className="flex items-center">
          {(result || isError) ? (
            isError ?
              <p className="text-xs/4 text-red-500"> {error?.toString()}</p>
              : <p className="text-xs/4 text-gray-500"> Ran at {result?.timestamp}</p>
          )
            : <SecondaryButton onClick={onClick} loading={isRunning}> Run </SecondaryButton>}
        </div>
      </li>
    </ul>
  );
};

export default Instruction;
