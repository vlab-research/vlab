import Extraction from './Extraction';
import {
  DataSource as DataSourceType,
  SourceExtraction as SourceExtractionType,
  Extraction as ExtractionType,
} from '../../../../types/conf';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericListFactory } from '../../components/GenericList';
import { blankConf } from './generateLookupConfs';

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

// One component for every source. Location says where to read and mapping says
// what the value means, and neither is a property of the connector, so all a
// source decides is which response values its payload offers.
const SourceExtraction: React.FC<Props> = ({ source, dataSource, setData, nameOptions, data, multipleSources }) => {

  const handleUserVariableChange = (e: any) => {
    const user: string = e.target.value;
    setData(source, { ...data, user_variable: user || undefined })
  }

  const handleExtractionChange = (a: ExtractionType[]) => {
    setData(source, { ...data, extraction_confs: a })
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
          Element={Extraction}
          elementName="variable to extract"
          elementProps={{ nameOptions: nameOptions, source: dataSource.source }}
          data={data.extraction_confs}
          setData={handleExtractionChange}
          initialState={[blankConf()]}
        />
      </div>

    </div>
  )
}

export default SourceExtraction;
