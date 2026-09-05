import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Destination from './Destination';
import { Destination as DestinationType } from '../../../../types/conf';

// The form's labels are not associated with their controls, so a field is
// addressed by its `name` — which is also what the conf key is called.
const field = (container: HTMLElement, name: string) =>
  container.querySelector(`[name="${name}"]`) as HTMLSelectElement;

// Ref mode is a radio group, so the answer is which radio is checked rather
// than the value of any one of them. Queried by role and by conf value, not by
// the mode's display name — these tests are about what gets saved, and
// `refMode.test.ts` is where the wording is pinned.
const refMode = () =>
  (screen.getByRole('radio', { checked: true }) as HTMLInputElement).value;

const chooseRefMode = (mode: string) =>
  fireEvent.click(
    screen
      .getAllByRole('radio')
      .find(r => (r as HTMLInputElement).value === mode) as HTMLInputElement
  );

// The scenario the whole absent-is-a-real-state rule exists for.
//
// A destination saved before ref_mode existed resolves to the behaviour it
// already has. The control shows that, but nothing writes it back: an
// unrelated edit leaves the conf exactly as thin as it arrived, because
// writing a mode onto it would rewrite that study's ads on the next
// reconciliation run for no reason anyone asked for.
describe('a destination saved before ref_mode existed', () => {
  const stored: any = {
    type: 'messenger',
    name: 'fly messenger',
    initial_shortcode: 'mnchweek',
    welcome_message: 'Welcome!',
    button_text: 'OK',
    additional_metadata: null,
  };

  const renderIt = () => {
    const saved: DestinationType[] = [{ ...stored }];
    const update = jest.fn();

    const { container } = render(
      <Destination
        data={{ ...stored }}
        index={0}
        update={update}
        savedDestinations={saved}
      />
    );

    return { update, container };
  };

  it('shows the mode it actually runs under', () => {
    renderIt();

    expect(refMode()).toBe('metadata');
  });

  it('keeps the field absent through an unrelated edit', () => {
    const { update } = renderIt();

    fireEvent.change(screen.getByDisplayValue('Welcome!'), {
      target: { name: 'welcome_message', value: 'Hello!' },
    });

    const [conf] = update.mock.calls[update.mock.calls.length - 1];
    expect(conf.welcome_message).toBe('Hello!');
    expect('ref_mode' in conf).toBe(false);
  });

  it('warns before changing a mode that already has ads in flight', () => {
    const { update } = renderIt();

    expect(screen.queryByText(/rewrites every ad/i)).toBeNull();

    chooseRefMode('encoded');

    const [conf] = update.mock.calls[update.mock.calls.length - 1];
    expect(conf.ref_mode).toBe('encoded');
  });

  it('says what changing it costs, once the conf carries the new mode', () => {
    // The warning is driven by the saved conf against the edit in progress, so
    // re-rendering with the changed data is what a real edit looks like.
    render(
      <Destination
        data={{ ...stored, ref_mode: 'encoded' }}
        index={0}
        update={jest.fn()}
        savedDestinations={[{ ...stored }]}
      />
    );

    expect(screen.getByText(/rewrites every ad/i)).toBeInTheDocument();
  });
});

describe('a destination saved with an explicit mode', () => {
  const stored: any = {
    type: 'messenger',
    name: 'fly messenger',
    initial_shortcode: 'mnchweek',
    welcome_message: 'Welcome!',
    button_text: 'OK',
    additional_metadata: null,
    ref_mode: 'encoded',
  };

  it('preserves that mode through an unrelated edit', () => {
    // The counterpart of the absent case: a conf that states a mode keeps it,
    // because the forms spread `...data` rather than rebuilding the conf.
    const update = jest.fn();

    render(
      <Destination
        data={{ ...stored }}
        index={0}
        update={update}
        savedDestinations={[{ ...stored }]}
      />
    );

    fireEvent.change(screen.getByDisplayValue('Welcome!'), {
      target: { name: 'welcome_message', value: 'Hello!' },
    });

    const [conf] = update.mock.calls[update.mock.calls.length - 1];
    expect(conf.welcome_message).toBe('Hello!');
    expect(conf.ref_mode).toBe('encoded');
  });

  it('does not warn while the mode still matches what was loaded', () => {
    render(
      <Destination
        data={{ ...stored }}
        index={0}
        update={jest.fn()}
        savedDestinations={[{ ...stored }]}
      />
    );

    expect(screen.queryByText(/rewrites every ad/i)).toBeNull();
  });
});

describe('a destination being added now', () => {
  it('states its mode, because it is a new conf', () => {
    const update = jest.fn();

    const { container } = render(
      <Destination data={{ type: '' }} index={0} update={update} />
    );

    fireEvent.change(field(container, 'destination_type'), {
      target: { value: 'messenger' },
    });

    expect(update).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'messenger', ref_mode: 'metadata' }),
      0
    );
  });
});

// Two destinations on one page. The browser groups radios by DOM `name`, so
// a shared name made every destination's ref-mode radios one group: choosing
// a mode on one destination unchecked the other's. The name is now suffixed
// with the destination's index, and the change event still reports the conf
// key, so the fix is checked from both sides.
describe('two destinations on one page', () => {
  const stored = (name: string, ref_mode: string): any => ({
    type: 'messenger',
    name,
    initial_shortcode: 'mnchweek',
    welcome_message: 'Welcome!',
    button_text: 'OK',
    additional_metadata: null,
    ref_mode,
  });

  const renderBoth = () => {
    const first = stored('first', 'metadata');
    const second = stored('second', 'metadata');
    const update = jest.fn();

    render(
      <>
        <Destination
          data={first}
          index={0}
          update={update}
          savedDestinations={[first, second]}
        />
        <Destination
          data={second}
          index={1}
          update={update}
          savedDestinations={[first, second]}
        />
      </>
    );

    return { update };
  };

  const radiosOf = (index: number) =>
    screen
      .getAllByRole('radio')
      .filter(
        r => (r as HTMLInputElement).name === `ref_mode-${index}`
      ) as HTMLInputElement[];

  it('gives each destination its own radio group', () => {
    renderBoth();

    expect(radiosOf(0)).toHaveLength(2);
    expect(radiosOf(1)).toHaveLength(2);
    expect(screen.getAllByRole('radio', { checked: true })).toHaveLength(2);
  });

  it('lets the second destination change mode without unchecking the first', () => {
    const { update } = renderBoth();

    fireEvent.click(radiosOf(1).find(r => r.value === 'encoded')!);

    // Reported under the conf key, at the second destination's index.
    expect(update).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'second', ref_mode: 'encoded' }),
      1
    );
    const [conf] = update.mock.calls[update.mock.calls.length - 1];
    expect('ref_mode-1' in conf).toBe(false);

    // The first destination's choice survives in the DOM.
    expect(radiosOf(0).find(r => r.value === 'metadata')!.checked).toBe(true);
  });
});
