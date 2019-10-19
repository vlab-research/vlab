import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import TypeformCreate from '../../components/TypeformCreate';
import { Hook } from '../../services';
import { SurveyScreen } from '..';
import './Surveys.css';

const { Content, Sider } = Layout;

export const Survey = React.createContext(null);

const Surveys = props => {
  const [surveys, setSurveys] = Hook.useMountFetch({ path: '/surveys' }, []);
  const [selected, setSelected] = useState('0');

  return (
    <Layout style={{ height: '100%' }}>
      <Sider style={{ background: '#fff' }}>
        <Survey.Provider value={{ setSurveys }}>
          <TypeformCreate {...props} />
        </Survey.Provider>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          onClick={e => setSelected(e.key)}
          style={{ borderRight: 0 }}
        >
          {surveys.map((survey, id) => (
            <Menu.Item key={id}>
              {survey.shortcode}
              {'-'}
              {survey.title}
            </Menu.Item>
          ))}
        </Menu>
      </Sider>
      {surveys.length > 0 ? (
        <Content style={{ padding: '30px' }}>
          <SurveyScreen userid={surveys[selected].userid} formid={surveys[selected].id} />
        </Content>
      ) : null}
      {/* <div>
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
      </div> */}
    </Layout>
  );
};

export default Surveys;
