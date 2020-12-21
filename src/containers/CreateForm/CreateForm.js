import React, { useState, useContext } from 'react';
import PropTypes from 'prop-types';
import { useLocation, useHistory } from 'react-router-dom';
import {
  Form, Select, Input, Button, Checkbox, Space, Spin,
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

  const [loading, setLoading] = useState(false);
  // Get available typeform forms or authorize with Typeform
  const onFinish = async (values) => {
    setLoading(true);
    const dat = formatData(values);

    try {
      const survey = await createSurvey(dat);
      setSurveys(surveys => [survey, ...surveys]);
      history.go(-1);
    } catch (e) {
      setLoading(false);
      alert(`An error occurred while creating the form: ${e}`); // eslint-disable-line no-alert
      console.error(e); // eslint-disable-line no-console
    }
  };

  const [form] = Form.useForm();


  const setTypeformData = (data) => {
    form.setFieldsValue({ formid: data.id, title: data.title });
    history.go(-1);
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
    <Spin spinning={loading}>
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

          <Form.Item label="Form">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Form.Item
                name="title"
                style={{ display: 'inline-block', width: 'calc(50% - 8px)', margin: '10px 10px 10px 0' }}
                rules={[{ required: true, message: 'Please import a Typeform form.' }]}
              >
                <Input placeholder="Title" disabled />
              </Form.Item>
              <Form.Item
                name="formid"
                style={{ display: 'inline-block', width: 'calc(30% - 8px)', margin: '10px 10px 10px 0' }}
                rules={[{ required: true, message: 'Please import a Typeform form.' }]}
              >
                <Input placeholder="ID" disabled />
              </Form.Item>
              <TypeformCreate cb={setTypeformData}> IMPORT FROM TYPEFORM </TypeformCreate>
            </div>
          </Form.Item>

        </section>

        <section className="create-translation">
          <h2> Translation </h2>
          <Form.Item label="Destination">
            <Form.Item
              label="Self"
              style={{ display: 'inline-block', width: 'calc(30%)', margin: '0 0 0 50px' }}
              onChange={onSelfTranslating}
              name="translation_self"
              valuePropName="checked"
            >
              <Checkbox />
            </Form.Item>
            <Form.Item
              style={{ display: 'inline-block', width: 'calc(70% - 50px)' }}
              dependencies={['translation_self']}
              label="Other form"
              name="translation_destination"
            >
              <Select showSearch optionFilterProp="children" disabled={selfTranslating}>
                {surveys.map(s => (
                  <Select.Option key={s.id} value={s.id}>{s.prettyName}</Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Form.Item>

        </section>

        <section className="create-metadata">
          <h2> Metadata </h2>
          <Form.Item label="  " colon={false}>
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
                        <Input placeholder="Field" />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        wrapperCol={{ span: 100 }}
                        name={[field.name, 'value']}
                        fieldKey={[field.fieldKey, 'value']}
                        rules={[{ required: true, message: 'Missing value' }]}
                      >
                        <Input placeholder="Value" />
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
          </Form.Item>
        </section>


        <Form.Item style={{ marginTop: '4em' }} wrapperCol={{ offset: 8, span: 16 }}>
          <PrimaryBtn> CREATE </PrimaryBtn>
        </Form.Item>
      </Form>
    </Spin>
  );
};


CreateForm.propTypes = {
  surveys: PropTypes.arrayOf(PropTypes.object),
};


export default CreateForm;
