// import { useQuery, queryCache } from 'react-query';
// import useAuthenticatedApi from '../../../../hooks/useAuthenticatedApi';

// const queryKey = 'studyConf';

// const useTargeting = (campaign: string) => {
//   const targetingQuery = useTargetingQuery(campaign);

//   const isLoading = !targetingQuery.data;

//   const errorOnLoad = isLoading && targetingQuery.isError;

//   return {
//     data: targetingQuery.data ?? {},
//     isLoading,
//     errorOnLoad,
//     refetchData: () => {
//       queryCache.invalidateQueries(queryKey);
//     },
//   };
// };

// const useTargetingQuery = (campaign: string) => {
//   const { fetchTargeting } = useAuthenticatedApi();
//   return useQuery([queryKey, campaign], () => fetchTargeting({ campaign }));
// };

// export const clearCacheWhileRefetching = () => {
//   queryCache.invalidateQueries(queryKey);
// };

// export default useTargeting;
