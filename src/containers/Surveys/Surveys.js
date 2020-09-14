import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import TypeformCreate from '../../components/TypeformCreate';
import { Hook } from '../../services';
import { SurveyScreen } from '..';
import './Surveys.css';

const { Content, Sider } = Layout;
export const Survey = React.createContext(null);

function groupBy(arr, fn) {
  const m = new Map()
  arr.forEach(el => {
    const k = fn(el)
    m.set(k, m.has(k) ? [...m.get(k), el] : [el])
  })
  return Array.from(m.entries())
}

const Surveys = props => {
  const [survs, setSurveys] = Hook.useMountFetch({ path: '/surveys' }, []);
  const [selected, setSelected] = useState('0');
  
  const surveys = groupBy(survs, e => e['shortcode'])

  return (
    <Layout style={{ height: '100%' }}>
      <Sider width='300' style={{ background: '#fff', overflowX: 'hidden', overflowY: 'scroll'}}>
        <Survey.Provider value={{ setSurveys }}>
          <TypeformCreate {...props} />
        </Survey.Provider>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          onClick={e => setSelected(e.key)}
          style={{ borderRight: 0 }}
        >
          {surveys.map(([code, s], idx) => (
            <Menu.Item key={idx}>
              {`${code} - v${s.length}`}
            </Menu.Item>
          ))}
        </Menu>
      </Sider>
      {surveys.length > 0 ? (
        <Content style={{ padding: '30px' }}>
          <SurveyScreen formids={surveys[selected][1].map(s => s.id)} />
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
