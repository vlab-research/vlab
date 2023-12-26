import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import getNextConf from '../../../helpers/getNextConf';
import { useQueryClient } from 'react-query';
import { queryKey } from './useStudyConf';

const useCreateStudyConf = (
  message: string,
  studySlug: string,
  confKeys: string[],
  confKey: string
) => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryClient = useQueryClient()

  const { createStudyConf } = useAuthenticatedApi();

  const { mutate: createStudyConfMutation, isLoading, isError } = useMutation(
    ({ data, confType, studySlug }: { data: any; confType: string; studySlug: string }) =>
      createStudyConf({ data, studySlug, confType }),
    {
      onSuccess: () => {
        if (getNextConf(confKeys, confKey)) {
          history.push(
            `/studies/${studySlug}/${getNextConf(confKeys, confKey)}`
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
        notyf.error({
          message: `${error.message}`,
          dismissible: true,
        });
      },
      onSettled: () => {
        queryClient.invalidateQueries(queryKey)
      },
    }
  );

  return {
    createStudyConf: createStudyConfMutation,
    isLoadingOnCreateStudyConf: isLoading,
    errorOnCreateStudyConf: isError,
  };
};

export default useCreateStudyConf;
