# Live smoke study — Nigeria (Kwara), encoded ref, three destination arms

**Status:** draft for review. Nothing created.
**Purpose:** the end-to-end test that has never been run — adopt mints a ref token,
Meta serves the ad, a real respondent clicks, fly decodes, swoosh joins
`ad_attributions.ref_token`, and the answer lands in `inference_data`. Plus the
payment path, which no probe can exercise.

## Parameters

| | |
|---|---|
| State | **Kwara** (North Central, ~3.5M) |
| Why Kwara | `ECD Diagnostic` is live in south-west, south-south, south-east and north-west. Kwara avoids bidding against a running study in the same auction. Ilorin gives enough urban Meta penetration to fill the sample. |
| Budget | $10 ad spend |
| Incentive | ₦500 airtime via Reloadly |
| `max_sample` | 10 **per arm**, 30 total (≈₦15,000 ≈ $10) |
| Arms | `messenger`, `whatsapp`, `multi` — one stratum each (a stratum may not mix channels) |
| `ref_mode` | `encoded` on all three — this is the mechanism under test |
| Extraction | one `mapping: "ad_table_lookup"` conf, or nobody is attributed |

Three strata × one creative = three ads, three `ad_attributions` rows, three
distinct `ref_token`s. A failure is attributable to one arm.

## Instrument

Six questions, ~3 minutes. Items are verbatim Afrobarometer R10 or verbatim Pew,
chosen because their wording is standard across AB countries — the Kenya-specific
option lists (education, ethnicity, party) do not port to Nigeria and are excluded.

**Screener**

1. *How old are you?* — open numeric (AB Q1). Under 18 → thank and exit **before**
   any reward is mentioned.

**Substantive**

2. *Are you a man or a woman?* — Man / Woman / Prefer not to say (AB Q101)
3. *How concerned are you about how companies use the data they collect online
   about you?* — Very concerned / Somewhat concerned / Not too concerned / Not at
   all concerned / Don't know (**Pew, verbatim from the US instrument**, Appendix B)
4. *For each of the following statements, please tell me whether you disagree or
   agree: When jobs are scarce, men should have more rights to a job than a woman.*
   — Strongly disagree / Disagree / Neither agree nor disagree / Agree / Strongly
   agree (AB Q49B)
5. *How much do you trust other Nigerians?* — Not at all / Just a little /
   Somewhat / A lot (AB Q87C)
6. *How often do you use the internet?* — Every day / A few times a week / A few
   times a month / Less than once a month / Never (AB Q90J)

Q3 is the only item kept verbatim from the US instrument rather than swapped, so
it is directly comparable to the existing US data. Q6 is the sharpest read on
frame bias: a Meta-recruited sample should be near-universally "Every day".

Four distinct scale shapes plus one open numeric — useful coverage of the form
engine for something this short.

**Payment**

Phone number → mobile operator (Glo / MTN / Airtel / 9mobile) → the
`payment:reloadly` wait statement, exactly the `bauchiendpayENG` pattern:

```json
{"type": "wait",
 "wait": {"type": "external", "value": {"type": "payment:reloadly", "id": "payment1"}},
 "payment": {"provider": "reloadly", "key": "<credentials key>",
             "details": {"number": "{{field:phone_number}}", "amount": 500,
                         "country": "NG", "operator": "{{field:mobile_provider}}",
                         "tolerance": 0, "id": "payment1"}}}
```

**Recontact — after payment lands**

7. *Thank you — your ₦500 airtime is on its way. We sometimes run other short
   surveys like this one, with the same kind of reward. Would you like us to
   contact you when we do?* — Yes / No
8. *(if Yes)* *What email address should we use?* — free text, skippable

Asking after paying is deliberate: the reward is not conditional on handing over
contact details.

## Consent

Adapted from `ecdenglish` (English, Nigeria, same org), which runs six statement
screens then an electronic-signature question. Three things must change and are
flagged below rather than silently copied.

### Draft

**Screen 1 — Purpose**

> You are invited to take part in a short research survey run by Virtual Lab. The
> purpose of this survey is to test our survey system and to collect general
> opinions from adults in Nigeria. To take part you must be 18 or older. You were
> selected because you clicked on our advertisement on Facebook, Instagram or
> WhatsApp.

**Screen 2 — Participation and withdrawal / duration**

> *Participation and withdrawal:* Your participation is completely voluntary. You
> can refuse to answer any question, or end the survey at any time, with no
> penalty.
>
> *Procedures and duration:* We will ask you six short questions about your
> opinions. This will take about 3 minutes.

**Screen 3 — Risks, benefits, prize**

> *Risks and Benefits:* There is a minimal risk to privacy when using online
> platforms. All responses are stored on encrypted systems and handled using
> strict data security protocols. There are no physical risks.
>
> *Prize for participation:* You will receive ₦500 in mobile credit for completing
> the survey.

**Screen 4 — Confidentiality**

> *Confidentiality and Data Privacy:* Your responses are confidential to the
> extent permitted by law. Only authorized members of the research team can access
> the data, which is stored on encrypted, password-protected systems. Personally
> identifiable information you give us — your phone number, and your email address
> if you choose to share it — is stored separately from your survey answers and
> deleted within two years.

**Screen 5 — Platform caveats** *(must be platform-neutral, see flag 2)*

> Messages are sent through Facebook Messenger or WhatsApp and are initially
> linked to your account on that service. Messages in business chats are not
> end-to-end encrypted and are subject to Meta's standard platform policies,
> including data retention and moderation. Deleting the conversation on your end
> does not remove copies Meta retains under its own policies.
>
> This survey uses an automated chatbot and is not monitored in real time. We
> cannot respond to individual reports of harm, abuse or criminal activity. If you
> are in danger or need support, please contact local authorities or a trusted
> service provider.

**Screen 6 — Data use and contact**

> *Data Use:* Your responses may be used to create a de-identified dataset, with
> information that could identify you removed. This may be used to improve our
> survey methods and may be used in future research. If you do not finish the
> survey, answers you have already given may still be used.
>
> *Questions and Contact:* Data collection for this study is managed by Virtual
> Lab. If you have questions, or wish to request that your personal data be
> deleted, email privacy@vlab.digital.

**Screen 7 — Electronic signature**

> By choosing 'Yes', you confirm that you have read and understood the above and
> agree to take part. A copy of this consent is available in this chat — you may
> screenshot or save it before continuing.

→ *Do you agree to take part?* Yes / No. **No → thank and exit.**

### Flags

1. **No IRB claim.** `ecdenglish` states approval from HML IRB and gives a World
   Bank contact. We have neither for this study, so those lines are removed rather
   than copied. Whether this needs review at all is a judgement call: it is a
   system test, but it asks attitude questions, collects PII, and builds a
   recontact list intended for future surveys. The recontact list is the part most
   worth checking with whoever handles ethics review — a one-off platform test is
   easier to justify than a standing panel.

2. **`ecdenglish`'s consent is Messenger-specific** — "Messages are sent through
   Facebook Messenger and initially linked to your Messenger account." We are
   fielding a WhatsApp arm and a multi arm, so that sentence would be false for
   two of three arms. Screen 5 above is neutral. If we would rather be exact, the
   arms need separate forms, which costs us the single-form comparison.

3. **Duration and prize must match reality.** ECD says 15 minutes and ₦1,000;
   ours is ~3 minutes and ₦500. Stated above; worth re-checking against the built
   form before fielding, since an inaccurate consent is the easiest thing to ship
   by accident when adapting.

## Open

- Reloadly credentials `key` for this study
- Whether the recontact list needs its own retention/consent treatment
- Whether to field all three arms at once or messenger+whatsapp first (the multi
  WhatsApp arm has never been observed; if the symmetry inference is wrong those
  respondents land in `FALLBACK_FORM` 305, another researcher's live survey).
  `RecruitmentAdArrivalsInFallback` fires at ≥2 such arrivals in an hour.
