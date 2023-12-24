import { useStudyQuery } from '../../StudyPage/hooks/useStudy';

const useStudy = (slug: string) => {
  const studyQuery = useStudyQuery(slug);
  const isLoading = !studyQuery.data;

  return {
    name: studyQuery.data?.name,
    slug: slug,
    isLoading,
  }
}

export default useStudy;
