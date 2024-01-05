import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { getNextConf } from '../shared';
import { useQueryClient } from 'react-query';
import { queryKey } from './useStudyConf';

const useCreateStudyConf = (
  message: string,
  studySlug: string,
  confKey: string
) => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryClient = useQueryClient()

  const { createStudyConf } = useAuthenticatedApi();

  const { mutate: createStudyConfMutation, isLoading, isError } = useMutation(
    ({ data, confType, studySlug }: { data: any; confType: string; studySlug: string }) =>


      createStudyConf({ data, studySlug, confType: confType.replace("_", "-") }),
    {

      onMutate: async () => {
        // or push to globalData here for optimistic updating
      },
      onSuccess: () => {
        queryClient.invalidateQueries(queryKey)

        if (getNextConf(confKey)) {
          history.push(
            `/studies/${studySlug}/${getNextConf(confKey)}`
          );
        } else {
          history.push(`/studies/`);
        }
        notyf.success({
          message: message,
          background: 'rgb(67 56 202)',
        });
      },
      onError: (error: any) => {
        queryClient.invalidateQueries([queryKey, studySlug])

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
    createStudyConf: createStudyConfMutation,
    isLoadingOnCreateStudyConf: isLoading || !!queryClient.isFetching(),
    errorOnCreateStudyConf: isError,
  };
};

export default useCreateStudyConf;
