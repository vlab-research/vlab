import { useState } from 'react';
import { Link } from 'react-router-dom';
import { InfoBanner } from '../../../components/InfoBanner';
import ConfWrapper from './ConfWrapper';
import useStudyErrors from '../hooks/useStudyErrors';
import { StudyError } from '../../../types/study';

const hasErrorSeverity = (errors: StudyError[]) =>
  errors.some(e => e.severity === 'error');

// Fingerprint of the current error set: if it changes, a dismissed banner
// reappears (dismissal is per-session, not permanent).
const errorSignature = (errors: StudyError[]) =>
  errors
    .map(e => `${e.fingerprint}@${e.last_seen}`)
    .sort()
    .join('|');

const dismissKey = (studySlug: string) => `study-errors-dismissed:${studySlug}`;

const StudyErrorsBanner: React.FC<{ studySlug: string }> = ({ studySlug }) => {
  const { errors } = useStudyErrors(studySlug);
  const [dismissed, setDismissed] = useState(false);

  if (errors.length === 0 || dismissed) {
    return null;
  }

  const signature = errorSignature(errors);
  if (sessionStorage.getItem(dismissKey(studySlug)) === signature) {
    return null;
  }

  const dismiss = () => {
    sessionStorage.setItem(dismissKey(studySlug), signature);
    setDismissed(true);
  };

  const variant = hasErrorSeverity(errors) ? 'error' : 'warning';
  const message = `This study has ${errors.length} issue${
    errors.length === 1 ? '' : 's'
  }.`;

  return (
    <ConfWrapper>
      <InfoBanner
        variant={variant}
        message={message}
        action={
          <Link
            to={`/studies/${studySlug}/errors`}
            className="flex-none text-sm font-medium underline hover:opacity-70"
          >
            View
          </Link>
        }
        onDismiss={dismiss}
      />
    </ConfWrapper>
  );
};

export default StudyErrorsBanner;
