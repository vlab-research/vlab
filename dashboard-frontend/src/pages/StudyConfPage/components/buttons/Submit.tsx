import PrimaryButton from '../../../../components/PrimaryButton';

const Submit = (props: any) => {
  const { isLast, isCreateStudyForm } = props;

  return (
    <div className="p-6 text-right">
      {!isCreateStudyForm && !isLast ? (
        <PrimaryButton type="submit" testId="study-conf-next-button">
          Next
        </PrimaryButton>
      ) : (
        <PrimaryButton type="submit" testId="new-study-submit-button">
          Create
        </PrimaryButton>
        // TODO pass loading for spinner
      )}
    </div>
  );
};

export default Submit;
