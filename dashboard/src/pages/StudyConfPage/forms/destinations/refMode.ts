/**
 * The two ref modes, and the names we call them by.
 *
 * A recruitment ad carries a **ref**: the string Meta hands back when someone
 * clicks it. The ref is the entire link between "someone clicked this ad" and
 * "this response belongs to women, 25-34, in Kwara." `ref_mode` says what that
 * string carries.
 *
 * ## The names
 *
 * There are exactly two, and they are the same words in the dashboard, in
 * `documentation/ad-attributions.md`, and in how we talk about this internally:
 *
 * | name            | `ref_mode`   | the ref looks like                         |
 * |-----------------|--------------|--------------------------------------------|
 * | **plain ref**   | `"metadata"` | `creative.X.gender.women.form.Y`           |
 * | **encoded ref** | `"encoded"`  | `r.<base64url(v1|len|shortcode|token)>`    |
 *
 * Two things to know about that table. First, **"encoded" is the stored
 * value** -- the user-facing name and the wire value are deliberately the same
 * string, so there is nothing to keep in sync. Second, **"plain" is not**: it
 * maps to `"metadata"`, which names where the stratum rides rather than how the
 * ref reads. The stored value cannot change -- it is in every conf in the
 * database -- so the mapping is stated here and in the docs instead.
 *
 * Older notes in `planning/` say **thick** for plain, and **thin** for a third
 * mode that no longer exists in the UI. Prefer plain/encoded.
 *
 * ## Why name them at all
 *
 * The control used to be a question with two sentences for answers, and a
 * sentence cannot be referred to later -- not in a support conversation, not in
 * a doc, not by a researcher asking a colleague which one their study uses. A
 * defined term can. The sentences did not disappear; they moved into each
 * option's description, where they explain a name rather than stand in for one.
 *
 * ## Read side
 *
 * This is independent of the extraction conf's `mapping`, the read side.
 * Neither validates, gates or reads the other: they are separate confs, POSTed
 * to separate endpoints, each saving on its own terms in any order.
 */
import { RefMode } from '../../../../types/conf';

// Annotated rather than inferred, so the value keeps its literal type where a
// destination conf is built and the union still narrows.
export const METADATA_MODE: RefMode = 'metadata';
export const ENCODED_MODE: RefMode = 'encoded';

export type { RefMode };

// The name of the setting itself. Not "ref mode": `ref_mode` is what the field
// is called, but what the researcher is choosing is what their ads' refs are.
export const REF_MODE_LABEL = "This study's ad refs";

/**
 * Both modes, always. There is nothing to decide it from: what a ref carries is
 * a property of the ref, not of the channel carrying it, so every destination
 * type offers the same two.
 *
 * Each description says the one thing that decides it -- where the stratum data
 * comes out, and what it costs -- and names `ref_token` explicitly, because
 * that is the key a researcher joins on and they will not find it by guessing.
 */
export const refModeOptions = () => [
  {
    name: METADATA_MODE,
    label: 'Plain ref',
    description:
      'The ref spells the stratum out, so gender and region arrive as ' +
      'columns in your response data with nothing to join. The ref is long ' +
      'and editable anywhere the respondent can see it, so use this only ' +
      'where they cannot: Messenger hides it, WhatsApp does not.',
  },
  {
    name: ENCODED_MODE,
    label: 'Encoded ref',
    description:
      'The ref is a short code, so the respondent never sees anything ' +
      'readable. Strata come from the ad-attributions export instead, ' +
      'joined to your responses on ref_token. Works the same on every ' +
      'channel, which is why a study running on more than one should ' +
      'prefer it.',
  },
];

/**
 * What a stored conf actually does, and never what to write back.
 *
 * An absent `ref_mode` is a real state: the conf predates the field. It resolves
 * to the behaviour it already has, which is what makes the migration free -- so
 * this reports, and nothing writes its result onto a conf that arrived without
 * one. The default belongs to the empty-state constructors, which build new
 * confs, and the forms spread `...data`, so a field absent from a conf stays
 * absent through an unrelated edit.
 */
export const displayedRefMode = (stored: string | undefined): RefMode =>
  stored === ENCODED_MODE ? ENCODED_MODE : METADATA_MODE;

/**
 * Whether saving would change what a destination's ads emit.
 *
 * Compared through `displayedRefMode`, so an absent mode and an explicit
 * "metadata" count as the same thing -- they describe the same ads.
 */
export const refModeChanges = (
  saved: string | undefined,
  next: string | undefined
): boolean => displayedRefMode(saved) !== displayedRefMode(next);

/**
 * What changing a saved destination's mode costs.
 *
 * The ref is part of the creative and reconciliation compares creatives, so
 * changing it rewrites every ad in the study on the next run.
 */
export const REF_MODE_CHANGE_WARNING =
  'Changing this rewrites every ad in this study on the next run: real spend, ' +
  'possibly another Meta review, and the learning phase starting over. Live ' +
  'posts people have already shared will start pointing at the new link. ' +
  'Respondents who already arrived keep the attribution they came with.';
