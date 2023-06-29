import { Notyf } from 'notyf';
import { useMutation } from 'react-query';
import useAuthenticatedApi from '../../../../hooks/useAuthenticatedApi';
import { clearCacheWhileRefetching } from '../../../../helpers/cache';

const useDeleteDestination = () => {
  const notyf = new Notyf();
  const queryKey = 'destinations';

  const { deleteDestination } = useAuthenticatedApi();
  const [deleteDestinationMutation, { isLoading }] = useMutation(
    async ({ data, studySlug }: { data: any; studySlug: string }) =>
      await deleteDestination({ data, studySlug }),
    {
      onSuccess: () => {
        clearCacheWhileRefetching(queryKey);
        notyf.success({
          message: `Destination deleted!`,
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
    deleteRequest: deleteDestinationMutation,
    isDeleting: isLoading,
  };
};

export default useDeleteDestination;
