import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { useQueryClient } from 'react-query';
import { queryKey } from './useStudyConf';

const useCopyConfs = (
  message: string,
  studySlug: string,
) => {

  const notyf = new Notyf();
  const history = useHistory();
  const queryClient = useQueryClient()

  const { copyConfs } = useAuthenticatedApi();

  const { mutate: copyConfsMutation, isLoading, isError } = useMutation(
    ({ data, studySlug }: { data: any; studySlug: string }) =>
      copyConfs({ studySlug, data }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(queryKey)
        history.push(`/studies/${studySlug}/general`);

        notyf.success({
          message: message,
          background: 'rgb(67 56 202)',
        });
      },
      onError: (error: any) => {
        queryClient.invalidateQueries([queryKey, studySlug])

        console.log(error)

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
    copyConfs: copyConfsMutation,
    isLoading,
    isError
  };
};

export default useCopyConfs;
