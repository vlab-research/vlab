import PrimaryButton from '../../../../../components/PrimaryButton';

const Submit = (props: any) => {
  const { isLast } = props;

  return (
    <div className="p-6 text-right">
      {!isLast ? (
        <PrimaryButton type="submit" testId="new-study-next-button">
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
