import SecondaryButton from './SecondaryButton';

type Props = {
  name?: string;
  type?: 'button' | 'submit' | undefined;
  onClick?: () => void;
  loading?: boolean;
  className?: string;
};

const DeleteButton = ({ name, type, onClick, loading, className }: Props) => {
  return (
    <SecondaryButton
      name={name}
      size="100"
      type={type}
      className={className}
      testId={`delete-button`}
      icon="TrashIcon"
      loading={loading}
      onClick={onClick}
    >
      {''}
    </SecondaryButton>
  );
};

export default DeleteButton;
