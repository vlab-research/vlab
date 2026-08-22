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
import {
  lookupConfsFromVariables,
  mergeLookupConfs,
  wouldGenerateAnything,
} from './generateLookupConfs';

const ExtractionList = GenericListFactory<ExtractionType>();
const TextInput = GenericTextInput as TextInputI<SourceExtractionType>;

interface Props {
  source: string;
  dataSource: DataSourceType;
  nameOptions: string[];
  data: SourceExtractionType;
  multipleSources: boolean;
  /** The study's declared stratum variables, which generation reads from. */
  variableNames: string[];
  setData: (s: string, a: SourceExtractionType) => void;
}

const SourceExtraction: React.FC<Props> = ({ source, dataSource, setData, nameOptions, data, multipleSources, variableNames }) => {
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

  const handleGenerate = () => {
    handleExtractionChange(
      mergeLookupConfs(
        data.extraction_confs,
        lookupConfsFromVariables(variableNames)
      )
    );
  };

  const lookup = {
    fly: FlyExtraction,
    qualtrics: QualtricsExtraction,
    typeform: QualtricsExtraction,
  }
  type sourceType = "fly" | "qualtrics"
  const Element = lookup[dataSource.source as sourceType]

  // Generation is offered on fly sources only, for the same reason the ad
  // lookup mapping is: Qualtrics and Typeform carry no ad token, so confs
  // generated there would yield nothing, forever and silently.
  const canGenerate = dataSource.source === 'fly';
  const generateAdds = wouldGenerateAnything(
    data.extraction_confs,
    variableNames
  );

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
      {canGenerate && (
        <div className="ml-8 my-4">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!generateAdds}
            className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md border ${
              generateAdds
                ? 'text-indigo-700 bg-indigo-50 border-indigo-200 hover:bg-indigo-100'
                : 'text-gray-400 bg-gray-50 border-gray-200 cursor-not-allowed'
            }`}
          >
            Add a variable for each stratum, from the ad that recruited them
          </button>
          <p className="mt-1 text-sm text-gray-500 w-4/5">
            {generateAdds
              ? 'Adds one row per variable you declared in Variables, read from the ad the respondent clicked. Nothing you have already filled in is changed.'
              : 'Every variable you declared already has a row here.'}
          </p>
        </div>
      )}
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
