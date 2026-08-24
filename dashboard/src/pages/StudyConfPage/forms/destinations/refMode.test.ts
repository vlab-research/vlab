import {
  REF_MODE_ENCODED,
  REF_MODE_THICK,
  displayedRefMode,
  initialRefMode,
  refModeConsequence,
  refModeOptions,
  refModeWouldChange,
} from './refMode';

describe('refMode', () => {
  describe('refModeOptions', () => {
    it('offers both modes, and takes nothing to decide that', () => {
      // The signature is the claim. This used to take the study's whole
      // destination list, so that thick could be withheld from anything but a
      // pure-Messenger study -- a form reasoning about other destinations to
      // decide what one destination may do. What a ref carries is a property
      // of the ref; the channel does not remove a mode.
      expect(refModeOptions().map(o => o.name)).toEqual([
        REF_MODE_ENCODED,
        REF_MODE_THICK,
      ]);
    });

    it('never offers a mode that is not encoded or thick', () => {
      // A ref either carries the stratum or carries a token that resolves to
      // it. "Carry neither" attributes nobody and is not something anyone
      // chooses.
      expect(new Set(refModeOptions().map(o => o.name))).toEqual(
        new Set([REF_MODE_ENCODED, REF_MODE_THICK])
      );
    });

    it('labels every option it offers', () => {
      refModeOptions().forEach(o => {
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
      // Absent means the conf predates this field, and adopt resolves it to
      // the inline ref.
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
      // Writing "metadata" onto a legacy conf changes no ad.
      expect(refModeWouldChange(undefined, REF_MODE_THICK)).toBe(false);
    });

    it('is true when a legacy conf is switched to encoded', () => {
      expect(refModeWouldChange(undefined, REF_MODE_ENCODED)).toBe(true);
    });

    it('is true when an explicit mode changes', () => {
      expect(refModeWouldChange(REF_MODE_ENCODED, REF_MODE_THICK)).toBe(true);
    });
  });

  describe('refModeConsequence', () => {
    it('sends the researcher to the export for an encoded study', () => {
      // The researcher-facing contract: with encoded, the stratum is not in the
      // survey data -- name where it is instead.
      expect(refModeConsequence(REF_MODE_ENCODED)).toContain(
        'ad-attributions export'
      );
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

    it('claims nothing about which channel a mode is for', () => {
      // Both consequence strings used to carry a "Messenger only" / "works the
      // same on every channel" clause, which was the coupling showing through
      // into the copy.
      [REF_MODE_ENCODED, REF_MODE_THICK].forEach(mode => {
        expect(refModeConsequence(mode)).not.toContain('Messenger');
        expect(refModeConsequence(mode)).not.toContain('WhatsApp');
      });
    });
  });
});
