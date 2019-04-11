import { useEffect, useState } from 'react';
import ApiClient from '../api';

export default function useMountFetch(fetchOpts, initialState) {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    ApiClient.fetcher(fetchOpts)
      .then(res => res.json())
      .then(data => setState(data));
  }, []);

  return state;
}
