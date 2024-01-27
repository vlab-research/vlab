import FlyExtraction from './FlyExtraction';
import QualtricsExtraction from './QualtricsExtraction';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import {
  DataSource as DataSourceType,
  SourceExtraction as SourceExtractionType,
  Extraction as ExtractionType,
} from '../../../../types/conf';

import { GenericListFactory } from '../../components/GenericList';


const ExtractionList = GenericListFactory<ExtractionType>();

interface Props {
  source: string;
  dataSource: DataSourceType;
  nameOptions: string[];
  data: SourceExtractionType;
  setData: (s: string, a: SourceExtractionType) => void;
}

const SourceExtraction: React.FC<Props> = ({ source, dataSource, setData, nameOptions, data }) => {
  const initialState: ExtractionType[] = [{
    name: '',
    location: '',
    key: '',
    functions: [],
    aggregate: '',
    value_type: ''
  }]

  // deal with user_variable --> with a select from variables from extraction_confs
  // const [useVariable, setUserVariable] = useState<string>("");

  const handleExtractionChange = (a: ExtractionType[]) => {
    setData(source, { extraction_confs: a })
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
