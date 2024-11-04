import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { useQueryClient } from 'react-query';
import { queryKey } from './useStudyConf';

const useRunInstruction = (

) => {
  const notyf = new Notyf();
  const queryClient = useQueryClient()

  const { runInstruction } = useAuthenticatedApi();

  const { mutate, isLoading, isError, data, error } = useMutation(
    ({ studySlug, instruction }: { studySlug: string, instruction: any }) =>

      runInstruction({ studySlug, instruction }),
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
      onError: () => {
        queryClient.invalidateQueries([queryKey])
      },
      onSettled: () => {

      },
    }
  );

  return {
    runInstruction: mutate,
    data: data?.data,
    isError,
    error,
    isLoading: isLoading || !!queryClient.isFetching(),
    errorOnCreateStudyConf: isError,
  };
};

export default useRunInstruction;
