import SecondaryButton from '../../../../../components/SecondaryButton';

const Button = ({ onChange }: any) => {
  const eventHandler = (e: any) => {
    onChange({ type: e.type });
  };
  return (
    <SecondaryButton
      testId={`add-button`}
      icon="PlusIcon"
      onClick={eventHandler}
    >
      {''}
    </SecondaryButton>
  );
};

export default Button;
