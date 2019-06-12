import React from 'react';
import { Link } from 'react-router-dom';
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
        <Link key={survey.id} to={`/surveys/details/${survey.shortcode}`}>
          <div className="title">{survey.title}</div>
        </Link>
      ))}
    </div>
  );
};

export default SurveysScreen;
