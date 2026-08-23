import {
  MESSENGER,
  REF_MODE_ENCODED,
  REF_MODE_THICK,
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
      expect(refModeOptions(messengerOnly).map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
        REF_MODE_THICK,
      ]);
    });

    it('withholds thick from every destination of a mixed study', () => {
      // Including its Messenger arm. Thick's cost — a visible, editable ref —
      // lands on the WhatsApp arm, so offering it anywhere in this study would
      // make one study attribute two different ways.
      expect(refModeOptions(withWhatsApp).map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
      ]);
    });

    it('offers encoded only on a whatsapp or multi study', () => {
      expect(refModeOptions(withMulti).map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
      ]);
    });

    it('never offers a mode that is not encoded or thick', () => {
      // "shortcode" — a clean ref that attributes nobody — is not part of this
      // module at all. No production conf resolves to it.
      const offered = [
        ...refModeOptions(messengerOnly),
        ...refModeOptions(withWhatsApp),
        ...refModeOptions(withMulti),
      ].map(o => o.name);

      expect(new Set(offered)).toEqual(
        new Set([REF_MODE_ENCODED, REF_MODE_THICK])
      );
    });

    it('labels every option it offers', () => {
      refModeOptions(messengerOnly).forEach(o => {
        expect(o.label).toBeTruthy();
        expect(o.label).not.toBe(o.name);
      });
    });
  });

  describe('displayedRefMode', () => {
    it('reports a stored mode as it is', () => {
      expect(displayedRefMode(REF_MODE_THICK)).toBe(REF_MODE_THICK);
      expect(displayedRefMode(REF_MODE_ENCODED)).toBe(REF_MODE_ENCODED);
    });

    it('reports an absent mode as thick', () => {
      // Absent means the conf predates this field, and every conf that predates
      // it is a thick Messenger one.
      expect(displayedRefMode(undefined)).toBe(REF_MODE_THICK);
    });

    it('never returns the UI default for an untouched conf', () => {
      // The property that keeps the migration free: nothing on the read path
      // may produce "encoded" out of an absent field, or a researcher would be
      // told their legacy study is something it is not.
      expect(displayedRefMode(undefined)).not.toBe(REF_MODE_ENCODED);
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
      expect(refModeWouldChange(undefined, undefined)).toBe(false);
    });

    it('is false when an absent mode is made explicit without changing it', () => {
      // Writing "metadata" onto a legacy Messenger conf changes no ad.
      expect(refModeWouldChange(undefined, REF_MODE_THICK)).toBe(false);
    });

    it('is true when a legacy conf is switched to encoded', () => {
      // The one flip that can actually occur, per the census: thick Messenger
      // to encoded, one direction, opt-in.
      expect(refModeWouldChange(undefined, REF_MODE_ENCODED)).toBe(true);
    });

    it('is true when an explicit mode changes', () => {
      expect(refModeWouldChange(REF_MODE_ENCODED, REF_MODE_THICK)).toBe(true);
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
      [REF_MODE_ENCODED, REF_MODE_THICK].forEach(mode => {
        expect(refModeConsequence(mode)).not.toContain('ref_mode');
      });
    });
  });

  it('exports MESSENGER as the type the whole-study check compares against', () => {
    expect(MESSENGER).toBe('messenger');
  });
});
