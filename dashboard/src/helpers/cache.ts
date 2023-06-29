import { queryCache } from 'react-query';

// TODO write test for this fn
export const addToCache = (data: object, queryKey: string) => {
  // Add data obj to cache
  queryCache.setQueryData(queryKey, (cache: any) => {
    const accountsCacheExists =
      Array.isArray(cache) &&
      cache[0] !== undefined &&
      Array.isArray(cache[0].data);

    if (accountsCacheExists === true) {
      cache[0].data = [data, ...cache[0].data];
    }

    return cache;
  });

  // Refetch the data by invalidating the query
  queryCache.invalidateQueries(queryKey);
};

export const clearCacheWhileRefetching = (queryKey: string) => {
  queryCache.invalidateQueries(queryKey);
};
