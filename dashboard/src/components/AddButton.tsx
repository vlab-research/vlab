import SecondaryButton from './SecondaryButton';

type Props = {
  onClick?: () => void;
  loading?: boolean;
};

const AddButton = ({ onClick, loading }: Props) => {
  return (
    <SecondaryButton
      size="100"
      testId={`add-button`}
      rounded={true}
      icon="PlusIcon"
      loading={loading}
      onClick={onClick}
    >
      {''}
    </SecondaryButton>
  );
};

export default AddButton;
