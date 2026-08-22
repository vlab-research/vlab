import {
  MESSENGER,
  REF_MODE_ENCODED,
  REF_MODE_THICK,
  REF_MODE_THIN,
  carriesRefMode,
  displayedRefMode,
  initialRefMode,
  isPureMessengerStudy,
  refModeConsequence,
  refModeOptions,
  refModeWouldChange,
} from './refMode';
import { Destination } from '../../../../types/conf';

const dest = (type: string): Destination => ({ type, name: type } as Destination);

const messengerOnly = [dest('messenger')];
const withWhatsApp = [dest('messenger'), dest('whatsapp')];
const withMulti = [dest('multi')];
const nonFly = [dest('website'), dest('app')];

describe('refMode', () => {
  describe('carriesRefMode', () => {
    it('covers the three fly destination types', () => {
      expect(carriesRefMode('messenger')).toBe(true);
      expect(carriesRefMode('whatsapp')).toBe(true);
      expect(carriesRefMode('multi')).toBe(true);
    });

    it('excludes web and app', () => {
      // Neither has an initial_shortcode: their url_template /
      // deeplink_template already points at a specific survey, so routing is
      // not a job the ref does for them and there is no mode to choose.
      expect(carriesRefMode('website')).toBe(false);
      expect(carriesRefMode('app')).toBe(false);
    });
  });

  describe('isPureMessengerStudy', () => {
    it('is true when every fly destination is messenger', () => {
      expect(isPureMessengerStudy(messengerOnly)).toBe(true);
    });

    it('ignores web and app destinations', () => {
      // They carry no ref mode, so they cannot make a study heterogeneous.
      expect(isPureMessengerStudy([...messengerOnly, ...nonFly])).toBe(true);
    });

    it('is false as soon as a whatsapp or multi destination exists', () => {
      expect(isPureMessengerStudy(withWhatsApp)).toBe(false);
      expect(isPureMessengerStudy(withMulti)).toBe(false);
    });

    it('is false for a study with no fly destinations at all', () => {
      expect(isPureMessengerStudy(nonFly)).toBe(false);
      expect(isPureMessengerStudy([])).toBe(false);
    });
  });

  describe('refModeOptions', () => {
    it('offers encoded and thick on a pure-messenger study', () => {
      expect(
        refModeOptions(MESSENGER, messengerOnly).map(o => o.name)
      ).toEqual([REF_MODE_ENCODED, REF_MODE_THICK]);
    });

    it('withholds thick from the messenger arm of a mixed study', () => {
      // Thick's cost — a visible, editable ref — lands on the WhatsApp arm, so
      // offering it here would make one study attribute two different ways.
      expect(refModeOptions(MESSENGER, withWhatsApp).map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
      ]);
    });

    it('never offers thick on whatsapp or multi', () => {
      expect(refModeOptions('whatsapp', withWhatsApp).map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
      ]);
      expect(refModeOptions('multi', withMulti).map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
      ]);
    });

    it('never offers thin, on any channel', () => {
      // Thin is a clean ref that attributes nobody. The census found no
      // production population on the channels that defaulted to it, so there is
      // no stored conf to preserve — making the footgun unreachable beats
      // discouraging it.
      const everywhere = [
        ...refModeOptions(MESSENGER, messengerOnly),
        ...refModeOptions('whatsapp', withWhatsApp),
        ...refModeOptions('multi', withMulti),
      ];
      expect(everywhere.some(o => o.name === REF_MODE_THIN)).toBe(false);
    });

    it('surfaces a stored legacy mode as a disabled current value', () => {
      // Showing a destination's real mode beats displaying one it does not
      // have, but it is a current value, not a choice.
      const options = refModeOptions('whatsapp', withWhatsApp, REF_MODE_THIN);
      const thin = options.find(o => o.name === REF_MODE_THIN);

      expect(thin).toBeDefined();
      expect(thin!.disabled).toBe(true);
    });

    it('does not duplicate a stored mode that is already offered', () => {
      const options = refModeOptions(MESSENGER, messengerOnly, REF_MODE_ENCODED);
      expect(options.filter(o => o.name === REF_MODE_ENCODED)).toHaveLength(1);
    });

    it('is empty for a destination type with no ref', () => {
      expect(refModeOptions('website', nonFly)).toEqual([]);
    });
  });

  describe('displayedRefMode', () => {
    it('reports a stored mode as it is', () => {
      expect(displayedRefMode(REF_MODE_THICK, MESSENGER)).toBe(REF_MODE_THICK);
      expect(displayedRefMode(REF_MODE_ENCODED, 'whatsapp')).toBe(
        REF_MODE_ENCODED
      );
    });

    it('reports an absent mode on messenger as thick, not as the UI default', () => {
      // Absent means the conf predates this field, and adopt resolves it from
      // the legacy include_metadata_in_ref flag — True on Messenger. Showing
      // "encoded" here would tell a researcher their legacy study is something
      // it is not.
      expect(displayedRefMode(undefined, MESSENGER)).toBe(REF_MODE_THICK);
    });

    it('reports an absent mode on whatsapp and multi as thin', () => {
      // Same resolution, opposite default: those channels default the legacy
      // flag False.
      expect(displayedRefMode(undefined, 'whatsapp')).toBe(REF_MODE_THIN);
      expect(displayedRefMode(undefined, 'multi')).toBe(REF_MODE_THIN);
    });

    it('never returns the UI default for an untouched conf', () => {
      // The property that keeps the migration free: nothing on the read path
      // may produce "encoded" out of an absent field.
      expect(displayedRefMode(undefined, MESSENGER)).not.toBe(REF_MODE_ENCODED);
      expect(displayedRefMode(undefined, 'whatsapp')).not.toBe(
        REF_MODE_ENCODED
      );
    });
  });

  describe('initialRefMode', () => {
    it('is encoded, so every new conf states its mode explicitly', () => {
      // Which is what makes an absent ref_mode in the database mean exactly one
      // thing: created before this feature existed.
      expect(initialRefMode()).toBe(REF_MODE_ENCODED);
    });
  });

  describe('refModeWouldChange', () => {
    it('is false for an untouched legacy conf', () => {
      // Opening a legacy destination and changing nothing is not a flip.
      expect(refModeWouldChange(undefined, undefined, MESSENGER)).toBe(false);
    });

    it('is false when an absent mode is made explicit without changing it', () => {
      // Writing "metadata" onto a legacy Messenger conf changes no ad.
      expect(refModeWouldChange(undefined, REF_MODE_THICK, MESSENGER)).toBe(
        false
      );
    });

    it('is true when a legacy messenger conf is switched to encoded', () => {
      // The one flip that can actually occur, per the census: thick Messenger
      // to encoded, one direction, opt-in.
      expect(refModeWouldChange(undefined, REF_MODE_ENCODED, MESSENGER)).toBe(
        true
      );
    });

    it('is true when an explicit mode changes', () => {
      expect(
        refModeWouldChange(REF_MODE_ENCODED, REF_MODE_THICK, MESSENGER)
      ).toBe(true);
    });
  });

  describe('refModeConsequence', () => {
    it('names ref_token for encoded, because that is the join key', () => {
      // The researcher-facing contract: with encoded, the stratum is not in the
      // survey data — give them the table and name the key.
      expect(refModeConsequence(REF_MODE_ENCODED)).toContain('ref_token');
    });

    it('says thick needs no join', () => {
      expect(refModeConsequence(REF_MODE_THICK)).toContain('nothing to join');
    });

    it('never says "ref_mode" to a researcher', () => {
      // Frame by consequence, not by mechanism.
      [REF_MODE_ENCODED, REF_MODE_THICK, REF_MODE_THIN].forEach(mode => {
        expect(refModeConsequence(mode)).not.toContain('ref_mode');
      });
    });
  });
});
