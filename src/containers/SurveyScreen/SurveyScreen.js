import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Switch, Route, useRouteMatch, useParams, Link,
} from 'react-router-dom';
import { Table, Spin } from 'antd';
import './SurveyScreen.css';
import { FormConfig } from '..';
import { groupBy } from '../../helpers';
import { CreateBtn, PrimaryBtn } from '../../components/UI';
import getCsv from '../../services/api/getCSV';

const Survey = ({ forms, selected }) => {
  const [downloading, setDownloading] = useState(false);
  const nameLookup = Object.fromEntries(forms.map(f => [f.id, f.prettyName]));

  const match = useRouteMatch();
  const getTranslationInfo = (record) => {
    if (record.translation_conf.self) {
      return 'self';
    }
    const dest = record.translation_conf.destination;
    if (dest && nameLookup[dest]) {
      return nameLookup[dest];
    }

    return null;
  };

  const grouped = groupBy(forms, f => f.shortcode);
  const data = [...grouped].map(([__, forms]) => forms[0]);
  const metadataFields = forms
    .map(f => f.metadata)
    .filter(md => md)
    .reduce((a, b) => [...a, ...Object.keys(b).filter(k => !a.includes(k))], []);

  let columns = ['shortcode', 'version', 'created', ...metadataFields]
    .map(f => ({ title: f, dataIndex: f, sorter: { compare: (a, b) => (a[f] > b[f] ? 1 : -1) } }));

  const ShortCodeLink = (text, record) => (
    <Link to={`${match.url}/data?shortcode=${record.shortcode}`}>
      {' '}
      {text}
      {' '}
    </Link>
  );

  columns[0] = {
    ...columns[0],
    render: ShortCodeLink,
  };

  columns[2] = {
    ...columns[2],
    render: text => (`${text.toLocaleDateString()} - ${text.toLocaleTimeString()}`),
  };

  const ActionLink = (text, record) => (<Link to={`create?from=${record.id}`}> new version </Link>);

  columns = [...columns,
    { title: 'translation', dataIndex: 'translation_conf', render: (text, record) => getTranslationInfo(record) },
    { title: 'actions', dataIndex: 'id', render: ActionLink },
  ];

  const PrettyNameLink = (text, record) => (
    <Link to={`${match.url}/data?surveyid=${record.id}`}>
      {record.prettyName}
    </Link>
  );

  const expandedRowRender = (row) => {
    const expanded = grouped.get(row.shortcode);
    const cols = [...columns];
    cols[0] = {
      title: 'form',
      dataIndex: 'prettyName',
      render: PrettyNameLink,
    };
    return (<Table columns={cols} dataSource={expanded} pagination={false} showHeader />);
  };

  const onDownload = async () => {
    setDownloading(true)
    await getCsv(selected)
    setDownloading(false)
  }

  return (
    <Spin spinning={downloading}>
      <div className="survey-table">
        <CreateBtn to={`/surveys/create?survey_name=${encodeURIComponent(selected)}`}> NEW FORM </CreateBtn>
        <PrimaryBtn onClick={onDownload}> DOWNLOAD CSV </PrimaryBtn>
        <Table
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 20 }}
          expandable={{ expandedRowRender, indentSize: 100 }}
        />
      </div>
    </Spin>
  );
};


const FormScreen = ({ forms }) => {
  const { surveyid } = useParams();
  const form = forms.find(s => s.id === surveyid);

  if (!form) {
    // redirect to 404 page
    return ('404!');
  }

  return (<FormConfig form={form} />);
};


const SurveyScreen = ({ forms, selected }) => {
  const match = useRouteMatch();

  return (
    <div>
      <Switch>
        <Route exact path={match.path}>
          <Survey forms={forms} selected={selected} />
        </Route>
        <Route exact path={`${match.path}/form/:surveyid`}>
          <FormScreen forms={forms} />
        </Route>
      </Switch>
    </div>
  );
};

Survey.propTypes = {
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
  selected: PropTypes.string.isRequired,
};

FormScreen.propTypes = {
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
};

SurveyScreen.propTypes = {
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
  selected: PropTypes.string.isRequired,
};

export default SurveyScreen;
