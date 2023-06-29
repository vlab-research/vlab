import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from './useAuthenticatedApi';
import { addToCache } from '../helpers/cache';

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
          duration: 2000,
        });
      },
      onError: error => {
        notyf.error({
          message: `${error.message}`,
          duration: 2000,
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
