# Goa'uld Grammar Specification

**Status:** reviewed working grammar for the translator app  
**Scope:** Standard Goa'uld with Jaffa, Tok'ra, Abydonian, and modern-fanon registers  
**Source of vocabulary:** `goauld_lexicon.yaml` plus curated runtime/language overlay `goauld_overrides.yaml`

This document turns the canon vocabulary and the reviewed fanon layer into a consistent working language.  It does **not** claim that Stargate canon contains a fully engineered language; it defines the app's disciplined reconstruction.

---

## 1. Design principles

1. **Canon first.** Canon terms are never replaced.  Fanon only specializes gaps or ambiguous canon fields.
2. **Culture first.** Goa'uld phrasing favors command, possession, hierarchy, ritual, and divine authority over neutral modern bureaucracy.
3. **Low morphology, high context.** Verbs do not inflect for person/tense.  Context, particles, and adverbs carry the load.
4. **One master lexicon.** A Goa'uld term owns its DE and EN senses together, so translations do not drift.
5. **Egyptian substrate is etymology, not a dump.** Egyptian roots may justify or inspire forms, but they stay low-priority unless reviewed.

---

## 2. Word order

Default order is **SVO**:

```text
Ta Kal'sha Lo.
I  love     you.
Ich liebe dich.
```

Adverbs normally appear where they are culturally emphatic:

```text
Re nok.        Come now. / Komm jetzt.
Nok, kree!     Now, attention! / Jetzt, Achtung!
```

Goa'uld tolerates ellipsis.  Articles and many auxiliaries are normally omitted:

```text
Lo Shol'va.    You are a traitor. / Du bist ein Verräter.
Ta ia Jaffa.   I am not Jaffa. / Ich bin kein Jaffa.
```

---

## 3. Articles and auxiliaries

There are no ordinary articles equivalent to **der/die/das/ein** or **the/a/an**.  The app drops them in sentence translation.

The copula **to be / sein** is usually implicit.  A reconstructed suffix **-k** may mark existence in lexicalized forms, but ordinary sentences should prefer zero-copula:

```text
Lo Shol'va.       You are a traitor.
Chappa'ai nok.    The Stargate is here.
```

---

## 4. Pronouns

| Function | Goa'uld | Status | Notes |
|---|---|---|---|
| I / me | `Ta` | canon/RDA, app-default | Default first-person pronoun. |
| I have / speaker-present | `Tel` | canon guide | Special form for possession/presence and preserved canon phrases. |
| you | `Lo` | canon/RDA | Singular second person. |
| we / us | `Tap` | canon-derived | `Ta` + plural `-p`. |
| you plural | `Lop` | canon-derived | `Lo` + plural `-p`. |
| he/she/it | `Ol` | fanon, needs care | Canon prefers names/titles instead of third-person pronouns. |
| they/them | `Olp` | fanon, needs care | Use sparingly; names/titles are more canonical. |

Examples:

```text
Ta ia Jaffa.       I am not Jaffa.
Lo Shol'va.        You are a traitor.
Tap re dan'kal'sha. We come in peace.
```

---

## 5. Plural

The plural marker is **-p** where it is morphologically accepted:

```text
Ta  → Tap    I → we
Lo  → Lop    you → you all
Ol  → Olp    he/she/it → they
```

For nouns, plural may be left contextual unless the lexicon has a reviewed plural form.  Do not attach `-p` mechanically to every noun in runtime output until a term has been reviewed.

---

## 6. Negation

| Form | Use | Examples |
|---|---|---|
| `ia` | sentence/predicate negation: not | `Ta ia Jaffa.` = I am not Jaffa. |
| `Ka` | no/none/kein; nominal negation or refusal | `Ka onak.` = No god. |
| `na-` | lexical antonym prefix only | `Na'dan` = false / un-true. |

Rules:

- Use `ia` before the predicate/action for ordinary **not**.
- Use `Ka` for standalone **no** or nominal **kein/keine/no/none**.
- Do **not** use `na-` as a sentence-negation shortcut.

---

## 7. Questions

Canon has compact, highly contextual interrogatives:

| Compact canon | Range |
|---|---|
| `Kel` | what/when/where/who depending on context |
| `Shal` | what/which and ritualized variants |

The app's extended precise mode uses reviewed fanon compounds:

| Meaning | Goa'uld | Derivation |
|---|---|---|
| who | `Kel'tar` | question + human/person |
| what | `Kel'shak` | question + act/event |
| where | `Kel'pac` | question + place/path |
| when | `Kel'nok` | question + now/time |
| how | `Kel'met` | question + condition/substance |

Examples:

```text
Kel'tar Shol'va?       Who is the traitor?
Kel'pac Chappa'ai?     Where is the Stargate?
Kel'nok tap re?        When do we come?
```

Canonical mode may still choose `Kel`/`Shal` as alternatives.

---

## 8. Demonstratives

| Meaning | Goa'uld | Notes |
|---|---|---|
| this / here | `Haka` | near/proximal deixis |
| that / there | `Hako` | far/distal deixis via `a → o` shift |

```text
Haka Chappa'ai.   This Stargate.
Hako ha'tak.      That Ha'tak.
```

---

## 9. Core tense and aspect markers

Goa'uld does not inflect verbs for tense.  Use time words:

| Meaning | Goa'uld | Notes |
|---|---|---|
| now/currently/here | `Nok` | canon |
| before/earlier | `nokia` | `Nok` + negation: not-now |
| later/afterwards | `Melnok` | fanon: after-now |

```text
Re nok.        Come now.
nokia Ta Jaffa. Before, I was Jaffa.
Melnok re.     Come later.
```

---

## 10. Modality

| Meaning | Goa'uld | Status | Notes |
|---|---|---|---|
| must / obligation | `Kree` | canon semantic extension | Command-force; not polite. |
| want / wish / will | `Kel'sha` | canon phrase extension | From “as you will / so be it”; needs context. |
| can / ability | `Dan'ryn` | low-priority fanon | Reviewed gap-fill, still marked `needs_review`. |

```text
Lo Kree Leaa.          You must listen.
Ta Kel'sha nem ron.    I want freedom.
Ta Dan'ryn Yu'yu.      I can see.
```

---

## 11. Core verb policy

| DE/EN | Goa'uld | Status |
|---|---|---|
| go / gehen | `Kree hol` | canon phrase, movement command |
| come / kommen | `Re` | canon/RDA |
| see / sehen | `Yu'yu` | reviewed fanon |
| hear/listen / hören | `Leaa` | canon/RPG |
| know/understand / wissen | `Eetium` | reviewed fanon |
| give/take / geben/nehmen | `Ko` | reviewed fanon/Unas transfer root |
| do/make / tun/machen | `Shak` | productive act/event root |
| say/speak / sagen/sprechen | `Meta` | extracted from canon phrase |

Verbs are uninflected:

```text
Ta Eetium.           I know.
Lo Meta dan.         You speak truth.
Tap Kree hol.        We go.
```

---

## 12. Nouns and core semantic conflicts

### Human field

| Concept | Goa'uld | Rule |
|---|---|---|
| Earth humans / humans in SG context | `Tau'ri` | default for human/humans |
| generic human/person | `Tar` | species/person without Earth context |
| humanity/humankind | `Tap'tar` | collective |
| human slave / servant | `Lo'taur` | hierarchy/status term |

### Size and power

| Concept | Goa'uld | Rule |
|---|---|---|
| god/divine power/great one | `Onak` | religious/imperial authority |
| physically large/big | `Tun'le` | size only |

### Love and emotion

| Concept | Goa'uld | Rule |
|---|---|---|
| inner feeling | `Sha` | productive emotion root |
| love / soul-bond | `Kal'sha` | default modern translation |
| fixed canonical love phrase | `Pal` | preserve in canon phrases |

---

## 13. Adjectives and intensification

Adjectives usually follow the noun they modify when the phrase is literal:

```text
ha'tak Tun'le      large Ha'tak
Jaffa nem ron      free Jaffa
```

The suffix **-le** intensifies or augments when the term is reviewed:

```text
Tun'le     physically large
Kek'le     very dead / lethal, where reviewed
```

Do not attach `-le` mechanically to unreviewed roots.

---

## 14. Registers

| Register | Style |
|---|---|
| `goauld_imperial` | divine, possessive, hierarchical; favors `Onak`, `Kree`, dominion compounds |
| `jaffa_military` | short commands, honor, obedience; favors `Kree`, `Tal shak`, direct imperatives |
| `tokra_resistance` | less god-centered, freedom/resistance vocabulary |
| `abydonian` | film/Egyptian-adjacent forms; keep distinct from standard Goa'uld |
| `modern_fanon` | practical app vocabulary for modern concepts; always marked as fanon |

---

## 15. Egyptian substrate policy

The app does not import Egyptian dictionaries as runtime vocabulary.  It keeps a curated substrate reservoir in `goauld_overrides.yaml`.

Promotion rules:

1. The concept must be culturally useful for Goa'uld.
2. No canon term may be displaced.
3. The Egyptian transliteration and TLA reference must be recorded.
4. The form must be phonologized into Goa'uld-compatible spelling.
5. The term starts at low `egyptian_substrate` priority.
6. Promotion requires review and examples.

Current approved/candidate substrate themes include name/identity (`rn → Ren`), divine power (`nṯr`, `sxm` as reservoir only), house/domain (`pr`), heart/mind (`ib`), life (`anx`), sun (`ra`), star/gate/teaching (`sbꜣ`), truth/order (`mꜣꜥt`), and speech (`mdw`).

---

## 16. Example corpus requirements

Every newly accepted word should have at least one example with:

```yaml
examples:
  - goauld: "Ta ia Shol'va."
    de: "Ich bin kein Verräter."
    en: "I am not a traitor."
    mode: literal
```

Long-term target: examples for more than 80% of high-priority lexicon entries.

---

## 17. Review statuses

| Status | Meaning |
|---|---|
| `draft` | Proposed but incomplete. |
| `needs_review` | Structured, but source/derivation or examples need review. |
| `needs_tla_id` | Egyptian-substrate candidate awaiting verified TLA numeric ID. |
| `approved_candidate` | Etymological candidate accepted as substrate, still low priority. |
| `approved` | May be used by runtime as normal reviewed data. |
| `deprecated` | Kept for compatibility, not preferred. |

---

## 18. Translator behavior summary

- YAML is the runtime source of truth.
- Sentence translation uses strict exact/primary-map matches, not fuzzy UI suggestions.
- Articles and pure auxiliaries are dropped.
- Semantic modals such as **must/can** and **muss/kann** are not stop words; they map through reviewed modal entries.
- Canonical mode can still prefer canon alternatives where a precise fanon form exists.
