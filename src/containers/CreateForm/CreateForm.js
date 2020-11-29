import React, { useState, useContext } from 'react';
import PropTypes from 'prop-types';
import { useLocation, useHistory } from 'react-router-dom';
import {
  Form, Select, Input, Button, Checkbox, Space,
} from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { Survey } from '../Surveys/Surveys';
import TypeformCreate from '../../components/TypeformCreate';
import typeformAuth from '../../services/typeform';
import { PrimaryBtn } from '../../components/UI';

const { createSurvey } = typeformAuth;

const formatData = (data) => {
  const md = data.metadata ? Object.fromEntries(data.metadata.map(o => [o.key, o.value])) : {};

  return {
    ...data,
    translation_conf: {
      self: data.translation_self,
      destination: data.translation_destination,
    },
    metadata: md,
  };
};

const reverseFormat = (data) => {
  const metadata = Object.entries(data.metadata).map(([k, v]) => ({ key: k, value: v }));
  return {
    ...data,
    metadata,
    translation_self: data.translation_conf.self,
    translation_destination: data.translation_conf.destination,
  };
};

const CreateForm = ({ surveys }) => {
  surveys.sort((a, b) => (a.prettyName > b.prettyName ? 1 : -1));

  const { setSurveys } = useContext(Survey);

  const location = useLocation();
  const history = useHistory();
  const query = new URLSearchParams(location.search);
  const from = query.get('from');

  const found = from && surveys.find(s => s.id === from);
  const formData = found ? reverseFormat(found) : { survey_name: query.get('survey_name') };

  // Get available typeform forms or authorize with Typeform
  const onFinish = async (values) => {
    const dat = formatData(values);

    try {
      const survey = await createSurvey(dat);
      setSurveys(surveys => [survey, ...surveys]);
      history.go(-1);
    } catch (e) {
      alert(`An error occurred while creating the form: ${e}`); // eslint-disable-line no-alert
      console.error(e); // eslint-disable-line no-console
    }
  };

  const [form] = Form.useForm();


  const setTypeformData = (data) => {
    form.setFieldsValue(data);
  };

  const [selfTranslating, setSelfTranslating] = useState(formData.translation_self);
  const onSelfTranslating = () => {
    const self = form.getFieldValue('translation_self');
    setSelfTranslating(self);

    if (self) {
      form.setFieldsValue({ translation_destination: undefined });
    }
  };


  return (
    <>
      <Form
        labelCol={{ span: 4 }}
        wrapperCol={{ span: 14 }}
        style={{ maxWidth: '1000px', marginLeft: 'auto', marginRight: 'auto' }}
        form={form}
        onFinish={onFinish}
        initialValues={formData}
        size="large"
      >

        <section>
          <h2> Survey </h2>
          <Form.Item
            label="Survey Name"
            name="survey_name"
            rules={[{ required: true, message: 'Please pick a name for the survey' }]}
          >
            <Input />
          </Form.Item>
        </section>

        <section>
          <h2> Form </h2>
          <Form.Item
            label="Shortcode"
            name="shortcode"
            rules={[{ required: true, message: 'Please pick a shortcode' }]}
          >
            <Input />
          </Form.Item>
        </section>

        <section className="create-typeform">
          <h2> Typeform </h2>
          <TypeformCreate cb={setTypeformData}> IMPORT FROM TYPEFORM </TypeformCreate>

          <Form.Item
            label="Typeform Form Title"
            name="title"
            rules={[{ required: true, message: 'Please import a Typeform form.' }]}
          >
            <Input disabled />
          </Form.Item>
          <Form.Item
            label="Typeform Form ID"
            name="formid"
            rules={[{ required: true, message: 'Please import a Typeform form.' }]}
          >
            <Input disabled />
          </Form.Item>
        </section>

        <section className="create-translation">
          <h2> Translation </h2>
          <Form.Item
            label="Self translate"
            onChange={onSelfTranslating}
            name="translation_self"
            valuePropName="checked"
          >
            <Checkbox />
          </Form.Item>
          <Form.Item dependencies={['translation_self']} label="Destination" name="translation_destination">
            <Select showSearch optionFilterProp="children" disabled={selfTranslating}>
              {surveys.map(s => (<Select.Option key={s.id} value={s.id}>{s.prettyName}</Select.Option>))}
            </Select>
          </Form.Item>

        </section>

        <section className="create-metadata">
          <h2> Metadata </h2>
          <Form.List name="metadata">
            {(fields, { add, remove }) => (
              <>
                {fields.map(field => (
                  <Space
                    key={field.key}
                    style={{
                      display: 'flex',
                      maxWidth: '800px',
                      marginBottom: 8,
                      marginRight: 'auto',
                      marginLeft: 'auto',
                    }}
                    align="baseline"
                  >

                    <Form.Item
                      {...field}
                      name={[field.name, 'key']}
                      fieldKey={[field.fieldKey, 'key']}
                      wrapperCol={{ span: 100 }}
                      rules={[{ required: true, message: 'Missing key' }]}
                    >
                      <Input placeholder="Key" />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      wrapperCol={{ span: 100 }}
                      name={[field.name, 'value']}
                      fieldKey={[field.fieldKey, 'value']}
                      rules={[{ required: true, message: 'Missing value' }]}
                    >
                      <Input placeholder="value" />
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(field.name)} />
                  </Space>
                ))}
                <Form.Item style={{
                  display: 'flex', maxWidth: '800px', marginBottom: 8, marginRight: 'auto', marginLeft: 'auto',
                }}
                >
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    Add Metadata
                  </Button>
                </Form.Item>
              </>
            )}
          </Form.List>
        </section>


        <Form.Item style={{ marginTop: '4em' }} wrapperCol={{ offset: 8, span: 16 }}>
          <PrimaryBtn> CREATE </PrimaryBtn>
        </Form.Item>
      </Form>
    </>
  );
};


CreateForm.propTypes = {
  surveys: PropTypes.arrayOf(PropTypes.object),
};


export default CreateForm;
