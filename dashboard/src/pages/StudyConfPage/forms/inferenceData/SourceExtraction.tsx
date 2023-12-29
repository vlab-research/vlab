import FlyExtraction from './FlyExtraction';
import QualtricsExtraction from './QualtricsExtraction';
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
  data: SourceExtractionType;
  setData: (s: string, a: SourceExtractionType) => void;
}

const SourceExtraction: React.FC<Props> = ({ source, dataSource, setData, data }) => {
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
  }
  type sourceType = "fly" | "qualtrics"
  const Element = lookup[dataSource.source as sourceType]

  if (!Element) {
    console.error(`We don't have a config for this source type: ${dataSource.source}`)
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
          elementProps={{}}
          data={data.extraction_confs}
          setData={handleExtractionChange}
          initialState={initialState}
        />
      </div>

    </div>
  )
}

export default SourceExtraction;
