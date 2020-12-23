import auth from '../auth';
import { Validator } from '../../helpers';

export default async function fetcher({
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

  const res = await fetch(URL, opts)

  if (!res.ok) {
    const r = await res.text()
    throw new Error(r)
  }

  return res
}
