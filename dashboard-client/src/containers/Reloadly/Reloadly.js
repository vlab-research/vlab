import React, { useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import LinkModal from '../../components/LinkModal';
import { Form, Input } from 'antd';
import api from '../../services/api';
import './Reloadly.css'

const Reloadly = () => {
  const history = useHistory();
  const back = () => history.go(-1);
  const [cred, setCred] = useState(null)
  const [form] = Form.useForm();

  const getCredentials = async () => {
    const res = await api.fetcher({
      path: '/credentials', method: 'GET',
    });
    const allCreds = await res.json();
    const rCred = allCreds.filter(e => e.entity === 'reloadly')[0];
    setCred(rCred);
    form.setFieldsValue({
      api_client_id: rCred && rCred.details && rCred.details.id ? rCred.details.id : '',
      api_client_secret: rCred && rCred.details && rCred.details.secret ? rCred.details.secret : ''
    });
  }

  const handleCreate = async () => {
    const id = form.getFieldValue('api_client_id');
    const secret = form.getFieldValue('api_client_secret');

    if (!id || !secret) {
      alert('You must provide valid credentials.');
      return;
    }

    const body = { entity: 'reloadly', key: '', details: { id, secret } };
    await api.fetcher({
      path: '/credentials', method: cred ? 'PUT' : 'POST', body, raw: true,
    });

    back();
  }

  useEffect(() => {
    getCredentials();
  }, []);

  const content = <>
    <span className="description">
      To connect to Reloadly provide your "API Client ID" and "API Client Secret". 
      You can find these values in the developers section once you have logged into Reloadly.
    </span>
    <Form
      form={ form }
      labelCol={{ span: 10 }}
      style={{ marginLeft: 'auto', marginRight: 'auto' }}
    >
      <Form.Item
        label="API Client ID"
        name="api_client_id"
        rules={[{ required: true, message: 'Please provide a valid value' }]}
      >
        <Input name="api_client_id" />
      </Form.Item>
      <Form.Item
        label="API Client Secret"
        name="api_client_secret"
        rules={[{ required: true, message: 'Please provide a valid value' }]}
      >
        <Input.Password name="api_client_secret" />
      </Form.Item>
    </Form>
  </>

  return (
    <LinkModal
      successText={ !cred ? "Create" : "Update" }
      title="Connect Reloadly"
      back={ back }
      loading={ cred === null }
      content={ content }
      success={ handleCreate }
    />
  );
};

Reloadly.propTypes = {};

export default Reloadly;
