# Project lineage, attribution and provenance audit

Last updated: 2026-08-19

This repository is maintained by `casama233`, but it is **not presented as an independently-originated RollPig implementation**.

## Felis direct resource overlay

The non-commercial AstrBot client can directly read and locally cache 34
allow-listed base resources from [Felis2026/rollpig-resources](https://github.com/Felis2026/rollpig-resources).
The overlay preserves the upstream source and attribution notice; it is not a
curryudon CDN, public Manifest mirror, or re-hosted public resource package.
Resource terms are documented in
[RESOURCES-LICENSE.md](https://github.com/Felis2026/rollpig-resources/blob/main/RESOURCES-LICENSE.md).

## Project lineage

The project has developed through work from multiple upstream projects and maintainers:

1. [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig) — original RollPig project and core concept/implementation lineage.
2. [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig) — AstrBot port and the direct GitHub parent of this repository.
3. [Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus) — a later RollPig Plus implementation whose feature design, command surface, protocols, user-facing copy and/or implementation have been referenced or adapted in parts during development of this enhanced AstrBot branch.

The current maintainer acknowledges that the repository previously did not make the third item sufficiently clear in the README, package metadata and license notices. That lack of attribution and source transparency is being corrected.

## Conservative credit-first policy

During this remediation the project deliberately uses a **credit-first / no-under-attribution** standard:

- when a later AstrBot feature has a material correspondence with a publicly documented RollPig Plus feature, command surface, state machine, resource protocol or distinctive user-facing expression, RollPig Plus is credited even when the present AstrBot implementation is structurally different;
- credit does **not** mean every listed local file is alleged to be a line-for-line copy;
- isolated generic programming/security techniques are not treated as proof of derivation, but a distinctive combination or workflow is still credited where appropriate;
- Bearlele/MegSopern lineage is preserved separately and is not incorrectly reassigned to Felis;
- artwork, prose and other resources remain subject to their own provenance and redistribution rights regardless of software attribution.

This policy is intentionally conservative while the detailed audit remains open.
The quarantine rule applies to public mirroring and redistribution; it does not
disable the separately documented Felis client-side direct-read overlay, which
uses the upstream address and keeps only a Bot-local operational cache.

## License notices

The software is distributed under the MIT License. The root [`LICENSE`](LICENSE) preserves copyright notices for upstream authors and current contributors, including:

- Bear_lele
- MegSopern
- Felis (`Felis2026`)
- casama233 and contributors

Where code has been copied, modified, translated between bot frameworks, or otherwise derived from an MIT-licensed upstream project, the upstream copyright and MIT permission notice remain applicable.

Attribution in this document is **not intended to re-license third-party artwork, images, text, datasets or other non-code material** for which the repository does not have redistribution rights.

## 2026-08 provenance audit

Following the attribution concerns raised in [AstrBotDevs/AstrBot#9687](https://github.com/AstrBotDevs/AstrBot/issues/9687), the maintainer is auditing later additions to this repository. The audit covers at least:

- daily-history / tomorrow-prediction / weekly-summary and PigHub discovery commands;
- permanent collection, image catalog, duplicate-growth / new-pig pity behavior;
- EX level / EX variant behavior and related resource formats;
- self-roast, roast-friend, random roast, force-mode and Roast Charge behavior;
- roast protection, roast reservation, participant / firewood flows and command naming;
- oven refill / charge recovery behavior;
- daily-report behavior, scheduling, labels and copy;
- public/private resource synchronization and resource metadata;
- PigHub fallback/cache behavior;
- local/shared/AI roast-copy behavior;
- copied or closely adapted user-facing text;
- images, resource packs and mirrored catalog entries;
- code paths whose structure or implementation may derive from RollPig Plus.

During the audit, similar functionality must not be described as wholly original merely because it was ported to AstrBot, rewritten, renamed, reorganized, or generated with AI assistance.

### Audit classification

Each disputed or overlapping item should be classified as one of the following:

- **Upstream inherited** — already present in Bearlele or MegSopern lineage.
- **MIT-derived from RollPig Plus** — code or substantial implementation derived from Felis2026's MIT-licensed project; preserve attribution and license notice.
- **Design/reference only** — similar feature idea, behavior or command design with an independently written implementation; credit the inspiration/source where appropriate.
- **Third-party resource** — image, prose, catalog data or other content requiring separate provenance/redistribution review.
- **Independent addition** — sufficiently documented independent work with no identified upstream dependency.

### Expanded feature-by-feature attribution matrix

The following matrix intentionally errs on the side of **crediting RollPig Plus wherever a material correspondence is currently identifiable**. A credit here is not a claim that every implementation is identical.

| Area | Attribution / classification | Current audit note |
| --- | --- | --- |
| Core `今日小猪` daily draw concept and original base catalog lineage | **Bearlele → MegSopern upstream inherited** | This is the pre-existing lineage of the direct AstrBot parent and must not be reassigned to Felis. |
| `昨日小猪` history view | **RollPig Plus feature/command-surface credit** | RollPig Plus publicly exposes the same history-view command family. Local implementation is credited conservatively while code-level derivation is checked. |
| `明日小猪` prediction | **RollPig Plus feature/command-surface credit** | Same distinctive daily-pig extension is present in RollPig Plus; local behavior may differ but the feature source is credited. |
| `随机小猪` and PigHub random discovery | **RollPig Plus feature/interaction credit; PigHub is a separate third-party service** | Use of PigHub itself is not owned by either project, but the RollPig Plus command/workflow correspondence is credited. |
| `找猪` / `搜猪` PigHub search | **RollPig Plus feature/command-surface credit** | Same PigHub search surface is present in RollPig Plus; implementation/fallback details are audited separately. |
| Permanent `我的猪圈` collection / summary | **RollPig Plus collection/growth design credit** | The direct MegSopern parent did not provide this enhanced collection system. RollPig Plus publicly exposes collection/growth behavior; local storage/read-model implementation has evolved independently in substantial ways. |
| Image catalog / collection card views | **RollPig Plus catalog presentation/design credit** | RollPig Plus has image-catalog rendering and collection presentation. Local renderer/layout code is not automatically classified as copied; visual/code-level comparison remains separate. |
| `本周小猪` weekly summary | **RollPig Plus feature/command-surface credit** | Same weekly-summary feature exists publicly in RollPig Plus; local renderer and history model may differ. |
| Duplicate growth / EX level progression / new-pig pity | **RollPig Plus growth-system design credit; implementation derivation under audit** | The grouped collection-growth semantics are materially aligned with RollPig Plus and are credited rather than presented as wholly original. |
| EX Lv.1–5 sparse variants (`pig_ex_variants.json`, `variant_images`, per-field inheritance) | **RollPig Plus-derived protocol/design; MIT-derived paths must retain notice** | The combination of EX 1–5, sparse levels, `image` / `description` / `analysis`, per-field inheritance, optional resource documents, staging/validation and same-version completion is too specific to describe as wholly independent. |
| `今日烤猪` self-roast / dish rendering | **RollPig Plus roast-system feature credit** | RollPig Plus publicly exposes the same self-roast concept. Local recipe/copy/rendering details require separate provenance checks. |
| `烤群友` group-member roast | **RollPig Plus roast-system design/command-surface credit** | RollPig Plus publicly exposes the same interaction family; isolated 60/30/10 probabilities alone are not treated as proof of code copying, but the overall feature system is credited. |
| Random group roast | **RollPig Plus interaction credit** | Same random-target roast family exists in RollPig Plus. Target-resolution/storage implementations are audited separately. |
| Force / expedited roast modes and `加急生火`-style surface | **RollPig Plus command/interaction credit** | Distinctive force-roast interaction and command surface are credited. Local compatibility aliases and superuser rules may differ. |
| Roast Charge / stored roast attempts / timed recovery | **RollPig Plus gameplay-system credit; implementation derivation under audit** | RollPig Plus publicly documents stored roast capacity and timed recovery; the local AstrBot token-bucket/storage implementation is credited at design level pending code-path comparison. |
| Roast protection / next-day protection | **RollPig Plus roast-system credit; implementation derivation under audit** | Protection is part of the same enhanced roast system and should not be presented as independently originated without stronger evidence. |
| Roast reservation / free firewood participation | **Strong RollPig Plus design/state-machine credit** | First participant becomes chef, chef pays normal cost, later participants join free, participant de-duplication, default 12 participants, target-draw trigger and 60/30/10 settlement materially correspond. Sampled current storage/delivery code differs substantially. |
| `/添柴` reservation support / contextual firewood flow | **RollPig Plus reservation/participation credit; local routing extensions separately authored unless evidence changes** | Reservation participation derives from the same feature family. The AstrBot contextual routing between refill and reservation is currently treated as a local extension on top of that credited concept. |
| Oven refill / group charge recovery | **RollPig Plus design/event/command credit; code-level derivation under audit** | Same gameplay name and refill concept are present in RollPig Plus. The local event lifecycle and storage implementation have evolved, but the source relationship is credited. |
| Daily report / scheduled group summary | **RollPig Plus group-summary feature credit** | RollPig Plus publicly exposes per-group daily summaries. Local scheduling, at-most-once delivery and rendering extensions do not erase the source feature relationship. |
| Daily-report labels `烧烤狂人` / `最惨食材` / `逃脱大师` / `反噬之王` | **Exact user-facing copy/statistical-design credit to RollPig Plus** | These four labels match exactly and are explicitly attributed. |
| Resource manifest sync / verified download / staging / rollback | **RollPig Plus resource-system implementation/design reference under path-level audit** | Individual safety techniques are common, but the combined manifest, size/SHA, staging, activation and rollback workflow warrants explicit RollPig Plus credit while derivation is audited. |
| PigHub endpoint fallback/cache workflow | **RollPig Plus implementation/design reference under audit** | PigHub itself is third-party; the more specific endpoint/fallback/cache behavior is credited where it corresponds to RollPig Plus. |
| Shared/local/AI roast copy fallback model | **RollPig Plus roast-copy system feature/design credit; text rights audited separately** | The feature combination of local/shared copy with optional AI fallback is present in RollPig Plus. Actual prose must have independent provenance or applicable permission. |
| EX resource editing/admin UI | **Underlying EX model credited to RollPig Plus; AstrBot admin UI implementation presently treated as local extension** | UI-specific code/layout is not automatically classified as copied, but it operates on the credited EX model/protocol. |
| Public resource source / submission-review service | **Local AstrBot service implementation, but any imported/mirrored RollPig Plus resources require separate source rights** | The service architecture itself is not credited to Felis absent stronger evidence; the historical Felis compatibility-floor resource import is a confirmed separate redistribution issue. |
| `吃群友` / random eat interaction | **Currently independent addition, subject to continued audit** | No corresponding feature has been identified in the checked current RollPig Plus public feature/command surface. This classification changes if contrary history is found. |
| SQLite authority/migrations, AstrBot identity-claim model, safe self-updater, admin analytics dashboard, Wiki, historical AI Pig Studio (retired from the current runtime), AstrBot Plugin Page integrations | **Currently independent/local engineering additions, subject to continued audit** | These are not treated as Felis-derived merely because both projects are RollPig variants. Specific copied text/code, if found later, must still be reclassified and credited. |

### Earlier evidence-specific mappings

For audit reproducibility, important source/history anchors already identified include:

- EX Lv.1–5 variants — RollPig Plus [`e1febd35`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/e1febd35ad85208e8a296e1828fb7fbdee29f672), local [`c1088a72`](https://github.com/casama233/astrbot_plugin_rollpig/commit/c1088a727a9e00f74e287a4d52e3ae80f21c4c8b).
- Roast reservation / participation — RollPig Plus [`76b25bbb`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/76b25bbb7fa34504f336dc956116da7350ec4357), local [`1e2bad06`](https://github.com/casama233/astrbot_plugin_rollpig/commit/1e2bad06d7dc3476f1b60b16268faf32d2a3ea03).
- Daily-report awards — RollPig Plus history including [`22b5357c`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/22b5357c3b6ae87fa5b048304cfab6913d83dda1), local [`1440a759`](https://github.com/casama233/astrbot_plugin_rollpig/commit/1440a759bf6506057592a112c92873accc729ebf).
- Oven refill — RollPig Plus [`1dcc8392`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/1dcc8392a463f4bfe7f339ede172417b4434bc7d), merged in [`36d0687c`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/36d0687c7fb26e087e8baea44afa2a960c677d34); local event lifecycle introduced in [`cb3d4099`](https://github.com/casama233/astrbot_plugin_rollpig/commit/cb3d4099a1abf120a38371a4dea3c2d5d9dc7474).
- PigHub fallback history — RollPig Plus [`b537cbb7`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/b537cbb7d11bad2afe2649c18bbc873608f860df) and later history.

The audit remains open for path-by-path classification. Until a path is verified, this document favors visible credit rather than an unsupported claim of independent origin.

## Resource distribution rule while audit is incomplete

Resources must not be assumed redistributable merely because related source code is MIT licensed. Any image, prose pack, catalog entry or other asset whose provenance or redistribution permission cannot be verified should be withheld from public distribution until the source and permission are confirmed.

For the historical `Felis2026/rollpig-resources` compatibility-floor import, **every restored ID is temporarily treated as unverified unless item-level provenance/permission has been established**. The safe temporary policy is therefore to remove/quarantine those restored records and images from the public mirror first, then restore only individually verified items.

Public-source submissions created independently by users should retain their own contributor/source metadata where available.

## Maintainer commitment

The maintainer will:

- keep upstream credits visible in README/license documentation;
- preserve required MIT copyright and permission notices;
- credit RollPig Plus conservatively across materially corresponding enhanced feature areas while the detailed audit remains incomplete;
- avoid claiming exclusive authorship over upstream-derived work;
- distinguish software licensing from artwork/content redistribution rights;
- remove or stop distributing material whose redistribution rights cannot be established;
- record material provenance corrections in public commits/PRs where possible;
- provide a contactable public path for future attribution reports.

Repository Issues have now been re-enabled and creation is allowed for all users, providing a direct public path for future attribution, license and provenance reports. The public [AstrBotDevs/AstrBot#9687](https://github.com/AstrBotDevs/AstrBot/issues/9687) thread also remains part of the remediation record.

If you believe a file, feature, resource or text is missing attribution, please report the exact path or item so it can be reviewed and corrected.
