import { useState } from 'react';
import FlyExtraction from './FlyExtraction';
import QualtricsExtraction from './QualtricsExtraction';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import {
  DataSource as DataSourceType,
  SourceExtraction as SourceExtractionType,
  Extraction as ExtractionType,
} from '../../../../types/conf';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericListFactory } from '../../components/GenericList';

const ExtractionList = GenericListFactory<ExtractionType>();
const TextInput = GenericTextInput as TextInputI<SourceExtractionType>;

interface Props {
  source: string;
  dataSource: DataSourceType;
  nameOptions: string[];
  data: SourceExtractionType;
  multipleSources: boolean;
  setData: (s: string, a: SourceExtractionType) => void;
}

const SourceExtraction: React.FC<Props> = ({ source, dataSource, setData, nameOptions, data, multipleSources }) => {
  const initialState: ExtractionType[] = [{
    name: '',
    location: '',
    key: '',
    functions: [],
    aggregate: '',
    value_type: ''
  }]

  const handleUserVariableChange = (e: any) => {
    const user: string = e.target.value;
    setData(source, { ...data, user_variable: user || undefined })
  }

  const handleExtractionChange = (a: ExtractionType[]) => {
    setData(source, { ...data, extraction_confs: a })
  }

  const lookup = {
    fly: FlyExtraction,
    qualtrics: QualtricsExtraction,
    typeform: QualtricsExtraction,
  }
  type sourceType = "fly" | "qualtrics"
  const Element = lookup[dataSource.source as sourceType]

  if (!Element) {
    return (
      <ErrorPlaceholder
        showImage={true}
        message={`Oops! We are missing a config for the source type: ${dataSource.source}`}
        onClickTryAgain={() => window.location.reload()}
      />
    )
  }

  return (

    <div>
      <h2 className="text-2xl">
        {source}
      </h2>
      {multipleSources &&
        <TextInput
          name="user_variable"
          handleChange={handleUserVariableChange}
          placeholder="Variable name to match user with the other source"
          value={data.user_variable}
          required={false}
        />}
      <div className="ml-8">
        <ExtractionList
          Element={Element}
          elementName="variable to extract"
          elementProps={{ nameOptions: nameOptions }}
          data={data.extraction_confs}
          setData={handleExtractionChange}
          initialState={initialState}
        />
      </div>

    </div>
  )
}

export default SourceExtraction;
