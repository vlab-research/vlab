import PrimaryButton from '../../../../components/PrimaryButton';

type NewAccountButtonProps = {
  testId: string;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

const NewAccountButton: React.FC<NewAccountButtonProps> = ({
  testId,
  open,
  setOpen,
}) => {
  const onClick = (e: any) => {
    setOpen(!open);
  };

  return (
    <PrimaryButton
      leftIcon="PlusCircleIcon"
      testId={testId}
      onClick={(e: any) => onClick(e)}
    >
      Add Account
    </PrimaryButton>
  );
};

export default NewAccountButton;
