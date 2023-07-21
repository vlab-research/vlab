import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Stratum from './Stratum';
import PrimaryButton from '../../../../components/PrimaryButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { createStrataFromVariables } from '../../../../helpers/strata';
import { GlobalFormData, Stratum as StratumType } from '../../../../types/conf';
import { GenericTextInput, TextInputI } from '../../components/TextInput';


export interface AdditionalStrataFormData {
  finishQuestionRef: string;
}
const AdditionalStrataTextInput = GenericTextInput as TextInputI<AdditionalStrataFormData>;


interface Props {
  id: string;
  localData: StratumType[];
  globalData: GlobalFormData;
  confKeys: string[];
}
const Variables: React.FC<Props> = ({
  globalData,
  id,
  localData,
  confKeys,
}: Props) => {
  const { variables, creatives, audiences } = globalData;

  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;

  const [formData, setFormData] = useState(localData || []);

  const [finishQuestionRef, setFinishQuestionRef] = useState();

  const regenerate = () => {
    const strata = createStrataFromVariables(variables, finishQuestionRef, creatives, audiences);
    setFormData(strata);
  };

  const updateFormData = (e: any, index: number): void => {
    const clone = [...formData];
    const { name, value } = e.target;
    clone[index] = { ...clone[index], [name]: value };
    setFormData(clone);
  };

  const onSubmit = (e: any) => {
    e.preventDefault();

    // caste quotas
    const data = { [id]: formData.map(s => ({ ...s, quota: +s.quota })) };
    createStudyConf({ data, studySlug });
  };

  const { createStudyConf } = useCreateStudyConf(
    true,
    'Strata saved',
    studySlug,
    confKeys,
    'strata'
  );

  const allCreatives = creatives ? creatives.map((c: any) => c.name) : [];

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <div className="py-2 text-left">
              <AdditionalStrataTextInput
                name="finishQuestionRef"
                type="text"
                value={finishQuestionRef}
                placeholder="The question ref of final question"
                handleChange={(e: any) => setFinishQuestionRef(e.target.value)}
              />
            </div>
            <div className="py-8 text-left">
              <PrimaryButton type="button" onClick={regenerate}>
                Generate from variables
              </PrimaryButton>
            </div>
            <form onSubmit={onSubmit}>
              <div className="mb-8">
                <ul>
                  {formData.length === 0 ? (
                    <li>
                      <div className="p-2 m-4"></div>
                      <div className="flex items-center justify-center h-40">
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                          className="flex-none fill-current text-gray-500 h-4 w-4"
                        >
                          <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm-.001 5.75c.69 0 1.251.56 1.251 1.25s-.561 1.25-1.251 1.25-1.249-.56-1.249-1.25.559-1.25 1.249-1.25zm2.001 12.25h-4v-1c.484-.179 1-.201 1-.735v-4.467c0-.534-.516-.618-1-.797v-1h3v6.265c0 .535.517.558 1 .735v.999z" />
                        </svg>
                        <p className="text-ml font-medium text-gray-700 ml-2">
                          First create some variables...
                        </p>
                      </div>
                    </li>
                  ) : (
                    formData.map((s, i) => (
                      <Stratum
                        key={i}
                        stratum={s}
                        onChange={(e: any) => updateFormData(e, i)}
                      />
                    ))
                  )}
                  {formData.length > 1 && (
                    <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                  )}
                </ul>
              </div>

              {formData.length !== 0 && (
                <div className="flex flex-row items-center">
                  <div className="text-left">
                    <PrimaryButton type="button" onClick={regenerate}>
                      Generate from variables
                    </PrimaryButton>
                  </div>
                  <span className="ml-4 italic text-gray-700 text-sm">
                    Generates strata from a set of variables
                  </span>
                </div>
              )}

              {formData.length !== 0 && (
                <div className="p-6 text-right">
                  <PrimaryButton type="submit" testId="form-submit-button">
                    Save
                  </PrimaryButton>
                </div>
              )}
            </form>
          </div>
        </div>
      </div >
    </div >
  );
};

export default Variables;
