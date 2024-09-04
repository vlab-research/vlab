import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { useQueryClient } from 'react-query';
import { queryKey } from './useStudyConf';

const useOptimize = (

) => {
  const notyf = new Notyf();
  const queryClient = useQueryClient()

  const { optimizeStudy } = useAuthenticatedApi();

  const { mutate: optimizeMutation, isLoading, isError } = useMutation(
    ({ studySlug }: { studySlug: string }) =>

      optimizeStudy({ studySlug }),
    {

      onMutate: async () => {
        // or push to globalData here for optimistic updating
      },
      onSuccess: () => {
        queryClient.invalidateQueries(queryKey)

        notyf.success({
          message: "optimized?",
          background: 'rgb(67 56 202)',
        });
      },
      onError: (error: any) => {
        queryClient.invalidateQueries([queryKey])

        // undo optimistic update...
        notyf.error({
          message: `${error.message}`,
          dismissible: true,
        });
      },
      onSettled: () => {

      },
    }
  );

  return {
    optimize: optimizeMutation,
    isLoading: isLoading || !!queryClient.isFetching(),
    errorOnCreateStudyConf: isError,
  };
};

export default useOptimize;
