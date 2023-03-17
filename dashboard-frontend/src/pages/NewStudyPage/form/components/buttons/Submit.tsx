import PrimaryButton from '../../../../../components/PrimaryButton';

const Submit = (props: any) => {
  const { isLast, isCreateStudyForm } = props;

  return (
    <div className="p-6 text-right">
      {!isCreateStudyForm && !isLast ? (
        <PrimaryButton type="submit" testId="study-configuration-next-button">
          Next
        </PrimaryButton>
      ) : (
        <PrimaryButton type="submit" testId="new-study-submit-button">
          Create
        </PrimaryButton>
      )}
    </div>
  );
};

export default Submit;
