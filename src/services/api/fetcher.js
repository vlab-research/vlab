import auth from '../auth';
import { Validator } from '../../helpers';

export default function fetcher({
  path = Validator.isRequired('path'),
  method = 'GET',
  headers = {},
  body,
}) {
  const URL = `${process.env.REACT_APP_SERVER_URL}/api/v1${path}`;
  const TOKEN = auth.getIdToken();

  const opts = { method, headers, body };
  if (method === 'POST' || method === 'PUT') opts.headers['Content-Type'] = 'application/json';
  if (body) opts.body = JSON.stringify(body);

  opts.headers.Authorization = `Bearer ${TOKEN}`;

  return fetch(URL, opts).catch(err => console.error('Error while fetching on this address', err)); // eslint-disable-line no-console
}
