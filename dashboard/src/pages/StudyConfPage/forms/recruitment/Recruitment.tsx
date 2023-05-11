import React, { useEffect, useState } from 'react';
import PipelineExperiment from './PipelineExperiment';
import Simple from './Simple';
import Form from '../../components/Form';

interface Props {
  id: string;
  data: FormData;
}

const Recruitment: React.FC<Props> = (props: Props) => {
  const lookup = [Simple, PipelineExperiment];
  const [index, setIndex] = useState<number>(0);
  const component = lookup[index];

  useEffect(() => {
    setIndex(index);
  }, [index]);

  const callback = (newIndex: number) => {
    setIndex(newIndex);
  };

  return <Form component={component} callback={callback} {...props}></Form>;
};

export default Recruitment;
