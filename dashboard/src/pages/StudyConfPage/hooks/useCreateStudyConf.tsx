import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import { addToCache } from '../../../helpers/cache';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';

const useCreateStudyConf = (redirect: boolean, message: string) => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryKey = 'studyConf';

  const { createStudyConf } = useAuthenticatedApi();

  const [createStudyConfMutation, { isLoading, error }] = useMutation(
    async ({ data, studySlug }: { data: any; studySlug: string }) =>
      await createStudyConf({ data, studySlug }),
    {
      onSuccess: ({ data: conf }) => {
        addToCache(conf, queryKey);
        if (redirect === true) {
          history.push(`/studies`);
        }
        notyf.success({
          message: message,
          background: 'rgb(67 56 202)',
        });
      },
      onError: error => {
        notyf.error({
          message: `${error.message}`,
          background: 'rgb(67 56 202)',
          dismissible: true,
        });
      },
    }
  );

  return {
    createStudyConf: createStudyConfMutation,
    isLoadingOnCreateStudyConf: isLoading,
    errorOnCreateStudyConf: error?.message,
  };
};

export default useCreateStudyConf;