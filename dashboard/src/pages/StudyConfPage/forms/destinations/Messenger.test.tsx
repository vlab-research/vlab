import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Messenger from './Messenger';
import { Messenger as MessengerType } from '../../../../types/conf';

/**
 * The one property this whole feature rests on: opening an existing destination
 * must never impose the UI's default mode on it.
 *
 * The model defaults `ref_mode` to absent and adopt resolves that per channel to
 * the study's historical behaviour, which is what makes this feature free to
 * migrate — nobody rewrites stored JSON. The dashboard defaults to encoded. The
 * two only coexist if the UI default is strictly a NEW-conf affordance, so these
 * tests exercise the failure it would otherwise cause: open a legacy thick
 * Messenger study, edit the welcome message, save, and silently flip a running
 * study's ads from thick to encoded.
 *
 * See planning/ref-mode-dashboard-ux.md §4.3 and forms/destinations/refMode.ts.
 *
 * Queried by role and placeholder rather than by label: the shared TextInput and
 * Select render a <label> with no `htmlFor`, so nothing associates it with its
 * control. Worth fixing, but it touches every form in the app and is not this
 * change's job.
 */

const legacy = (): MessengerType =>
  ({
    type: 'messenger',
    name: 'fly messenger',
    initial_shortcode: 'mnchweek',
    welcome_message: 'Welcome',
    button_text: 'OK',
    additional_metadata: null,
    // ref_mode deliberately absent: this is what every conf written before the
    // field existed looks like.
  } as MessengerType);

const renderForm = (data: MessengerType) => {
  const updateFormData = jest.fn();
  render(
    <Messenger
      data={data}
      index={0}
      updateFormData={updateFormData}
      destinations={[data]}
    />
  );
  return updateFormData;
};

describe('Messenger destination form', () => {
  it('shows a legacy conf as thick, not as the UI default', () => {
    renderForm(legacy());

    // The only select in this form; the destination-type select lives in
    // Destination.tsx, which is not rendered here.
    const select = screen.getByRole('combobox') as HTMLSelectElement;

    expect(select.value).toBe('metadata');
  });

  it('leaves ref_mode absent when an unrelated field is edited', () => {
    // The silent-flip scenario, exactly: edit the welcome message on a legacy
    // study and the conf must go back with no ref_mode at all.
    const updateFormData = renderForm(legacy());

    fireEvent.change(screen.getByPlaceholderText(/welcome to our survey/i), {
      target: { name: 'welcome_message', value: 'Hello there' },
    });

    expect(updateFormData).toHaveBeenCalledTimes(1);
    const [emitted] = updateFormData.mock.calls[0];

    expect(emitted.welcome_message).toBe('Hello there');
    expect('ref_mode' in emitted).toBe(false);
  });

  it('writes ref_mode only when the researcher changes it', () => {
    const updateFormData = renderForm(legacy());

    fireEvent.change(screen.getByRole('combobox'), {
      target: { name: 'ref_mode', value: 'encoded' },
    });

    const [emitted] = updateFormData.mock.calls[0];
    expect(emitted.ref_mode).toBe('encoded');
  });

  it('preserves an explicitly stored mode through an unrelated edit', () => {
    const updateFormData = renderForm({ ...legacy(), ref_mode: 'encoded' });

    fireEvent.change(screen.getByPlaceholderText('E.g OK'), {
      target: { name: 'button_text', value: 'Start' },
    });

    const [emitted] = updateFormData.mock.calls[0];
    expect(emitted.ref_mode).toBe('encoded');
  });

  it('warns about the ad rewrite once the mode diverges from what was loaded', () => {
    // Not about data loss — swoosh's extraction is additive and both eras
    // attribute. The cost is that the ref is part of the creative, so every ad
    // gets rewritten on the next reconciliation run.
    const data = legacy();
    const { rerender } = render(
      <Messenger
        data={data}
        index={0}
        updateFormData={jest.fn()}
        destinations={[data]}
      />
    );

    expect(screen.queryByText(/rewrites every ad/i)).not.toBeInTheDocument();

    const flipped = { ...data, ref_mode: 'encoded' } as MessengerType;
    rerender(
      <Messenger
        data={flipped}
        index={0}
        updateFormData={jest.fn()}
        destinations={[flipped]}
      />
    );

    expect(screen.getByText(/rewrites every ad/i)).toBeInTheDocument();
  });
});
