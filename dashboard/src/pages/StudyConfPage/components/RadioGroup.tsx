import { classNames } from '../../../helpers/strings';

export interface RadioOption {
  // The value written to the conf. Also half of each input's DOM id.
  name: string;
  // The defined term. Short enough to say in a sentence, because it is the
  // word the docs and support conversations use too.
  label: string;
  // What choosing it does to the researcher's data. One or two sentences.
  description?: string;
}

interface RadioGroupProps {
  name: string;
  label: string;
  options: RadioOption[];
  value: string;
  // Receives a native change event, so a form's existing
  // `({ name, value }) => ...` handler works unchanged.
  handleChange: (e: any) => void;
  disabled?: boolean;
}

/**
 * A small set of named, mutually exclusive choices, each shown with the
 * sentence that defines it.
 *
 * This exists because `<select>` cannot do that: an `<option>` renders flat
 * text, so a select can show either a name or an explanation, never a name
 * *and* its meaning at the moment of choosing. Squeezing the explanation into
 * the option text is what made the ref-mode control unreadable. Reach for this
 * whenever the options are terms the researcher is being taught rather than
 * values they already know.
 */
export const RadioGroup: React.FC<RadioGroupProps> = ({
  name,
  label,
  options,
  value,
  handleChange,
  disabled = false,
}) => (
  <fieldset className="sm:my-4">
    <legend className="my-2 block text-sm font-medium text-gray-700">
      {label}
    </legend>
    <div className="space-y-3">
      {options.map(option => (
        <div key={option.name} className="flex items-start">
          <input
            id={`${name}-${option.name}`}
            name={name}
            type="radio"
            value={option.name}
            checked={value === option.name}
            disabled={disabled}
            onChange={handleChange}
            className={classNames(
              'mt-1 h-4 w-4 shrink-0',
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            )}
          />
          <label
            htmlFor={`${name}-${option.name}`}
            className={classNames(
              'ml-3 block',
              disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            )}
          >
            <span className="block text-sm font-medium text-gray-900">
              {option.label}
            </span>
            {option.description && (
              <span className="block text-sm text-gray-500">
                {option.description}
              </span>
            )}
          </label>
        </div>
      ))}
    </div>
  </fieldset>
);
