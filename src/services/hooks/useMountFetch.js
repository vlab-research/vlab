import { useEffect, useState } from 'react';
import ApiClient from '../api';

export default function useMountFetch(fetchOpts, initialState) {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    ApiClient.fetcher(fetchOpts)
      .then(res => {
        try {
          const r = res.json();
          if (r.error) throw new Error(r.error);
        } catch (e) {
          console.error(`Error in fetch. RAW RESPONSE: ${res}`); //eslint-disable-line
          console.error(e); //eslint-disable-line
        }
      })
      .then(data => setState(data))
      .catch(e => console.error(e)); //eslint-disable-line
  }, []);

  return [state, setState];
}
