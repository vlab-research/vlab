import React from 'react';
import TypeformCreate from '../../components/TypeformCreate';
import { Hook } from '../../services';

export const Survey = React.createContext(null);

const SurveysScreen = props => {
  const [surveys, setSurveys] = Hook.useMountFetch({ path: '/surveys' }, []);

  return (
    <div>
      <Survey.Provider value={{ setSurveys }}>
        <TypeformCreate {...props} />
      </Survey.Provider>
      {surveys.map(survey => (
        <div key={survey.id} className="title">
          {survey.title}
        </div>
      ))}
    </div>
  );
};

export default SurveysScreen;
