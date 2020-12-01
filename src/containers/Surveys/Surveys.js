import React from 'react';
import {
  Switch, Route, useRouteMatch, useHistory, useParams,
} from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { CreateBtn } from '../../components/UI';
import { Hook } from '../../services';
import { SurveyScreen, CreateForm, DataScreen } from '..';
import './Surveys.css';
import { groupBy } from '../../helpers';

const { Content, Sider } = Layout;
export const Survey = React.createContext(null);

function sortForms(fo) {
  let forms = fo.map(f => ({ ...f, created: new Date(f.created) }));
  forms.sort((a, b) => (a.created > b.created ? 1 : -1));
  forms = forms
    .map((f, i) => ({ ...f, version: i + 1 }))
    .map(f => ({ ...f, key: f.id, ...f.metadata }));
  forms.sort((a, b) => (a.version > b.version ? -1 : 1));
  return forms;
}

const Surveys = () => {
  const [survs, setSurveys] = Hook.useMountFetch({ path: '/surveys' }, []);

  const match = useRouteMatch();
  const history = useHistory();
  const { survey: surveyParam } = useParams();
  const selected = decodeURIComponent(surveyParam);

  const formattedSurveys = [...groupBy(survs, f => f.shortcode)]
    .map(([code, forms]) => [code, sortForms(forms)])
    .reduce((a, [__, surveys]) => [...a, ...surveys], [])
    .map(s => ({ ...s, prettyName: `${s.shortcode} v${s.version}` }));

  const groupedByName = groupBy(formattedSurveys, e => `${e.survey_name}`);
  const surveys = [...groupedByName].reduce((a, [__, surveys]) => [...a, ...surveys], []);
  const forms = groupedByName.get(selected);

  return (
    <Layout style={{ height: '100%' }}>
      <Survey.Provider value={{ setSurveys }}>
        <Sider width="300" style={{ background: '#fff', overflowX: 'hidden', overflowY: 'scroll' }}>
          <CreateBtn to="/surveys/create"> NEW SURVEY </CreateBtn>
          <Menu
            mode="inline"
            selectedKeys={[selected]}
            onClick={e => history.push(`/surveys/${encodeURIComponent(e.key)}`)}
            style={{ borderRight: 0 }}
          >
            {Array.from(groupedByName.entries()).map(([name, s]) => (
              <Menu.Item key={name}>
                {`${name} (${s.length})`}
              </Menu.Item>
            ))}
          </Menu>
        </Sider>
        <Content style={{ padding: '30px' }}>
          <Switch>
            <Route exact path={`/${match.path.split('/')[1]}`}>
              No survey selected
            </Route>
            <Route path={`/${match.path.split('/')[1]}/create`}>
              <CreateForm surveys={surveys} />
            </Route>
            <Route path={`${match.path}/data`}>
              <DataScreen surveys={surveys} />
            </Route>
            <Route path={match.path}>
              {forms ? (<SurveyScreen forms={forms} selected={selected} />) : null}
            </Route>
          </Switch>
        </Content>
      </Survey.Provider>
    </Layout>
  );
};


export default Surveys;
