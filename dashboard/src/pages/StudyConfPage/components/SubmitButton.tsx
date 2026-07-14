import PrimaryButton from '../../../components/PrimaryButton';

const SubmitButton = ({ isLoading }: { isLoading: boolean }) => {
  return (
    <div className="p-6 text-right">
      <PrimaryButton
        leftIcon="CheckCircleIcon"
        type="submit"
        testId="form-submit-button"
        loading={isLoading}
      >
        Next
      </PrimaryButton>
    </div>
  )
}

export default SubmitButton
