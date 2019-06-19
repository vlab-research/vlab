import React, { useState } from 'react';
import { Select } from 'antd';
import TypeformCreate from '../../components/TypeformCreate';
import { Hook } from '../../services';
import { SurveyScreen } from '..';

import './Surveys.css';

export const Survey = React.createContext(null);

const Surveys = props => {
  const [surveys, setSurveys] = Hook.useMountFetch({ path: '/surveys' }, []);
  const [selected, setSelected] = useState(0);

  return (
    <div>
      <Survey.Provider value={{ setSurveys }}>
        <TypeformCreate {...props} />
      </Survey.Provider>
      {surveys.length ? (
        <>
          <Select
            defaultValue={selected}
            onSelect={value => setSelected(value)}
            dropdownRender={menu => <div>{menu}</div>}
          >
            {surveys.map((survey, id) => (
              <Select.Option key={survey.id} value={id}>
                {survey.title}
              </Select.Option>
            ))}
          </Select>
          <SurveyScreen userid={surveys[selected].userid} formid={surveys[selected].formid} />
        </>
      ) : null}
    </div>
  );
};

export default Surveys;
