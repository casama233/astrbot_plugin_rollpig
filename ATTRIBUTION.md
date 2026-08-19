# Project lineage, attribution and provenance audit

Last updated: 2026-08-19

This repository is maintained by `casama233`, but it is **not presented as an independently-originated RollPig implementation**.

## Project lineage

The project has developed through work from multiple upstream projects and maintainers:

1. [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig) — original RollPig project and core concept/implementation lineage.
2. [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig) — AstrBot port and the direct GitHub parent of this repository.
3. [Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus) — a later RollPig Plus implementation whose feature design, command surface and/or implementation have been referenced or adapted in parts during development of this enhanced AstrBot branch.

The current maintainer acknowledges that the repository previously did not make the third item sufficiently clear in the README, package metadata and license notices. That lack of attribution and source transparency is being corrected.

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

- EX level / EX variant behavior and related resource formats;
- roast-friend, roast reservation, participant / firewood flows and command naming;
- oven refill / charge recovery behavior;
- daily-report behavior, labels and copy;
- public/private resource synchronization and resource metadata;
- copied or closely adapted user-facing text;
- images, resource packs and mirrored catalog entries;
- code paths whose structure or implementation may derive from RollPig Plus.

During the audit, similar functionality must not be described as wholly original merely because it was ported to AstrBot, rewritten, renamed, or generated with AI assistance.

### Audit classification

Each disputed or overlapping item should be classified as one of the following:

- **Upstream inherited** — already present in Bearlele or MegSopern lineage.
- **MIT-derived from RollPig Plus** — code or substantial implementation derived from Felis2026's MIT-licensed project; preserve attribution and license notice.
- **Design/reference only** — similar feature idea, behavior or command design with an independently written implementation; credit the inspiration/source where appropriate.
- **Third-party resource** — image, prose, catalog data or other content requiring separate provenance/redistribution review.
- **Independent addition** — sufficiently documented independent work with no identified upstream dependency.

### Initial feature-by-feature mapping

The following is an initial good-faith mapping based on public history and sampled current implementations. It is deliberately more specific than labeling the entire repository either "copied" or "independent".

| Area | RollPig Plus public source | Local history | Initial classification | Current audit note |
| --- | --- | --- | --- | --- |
| EX Lv.1–5 variants | [`e1febd35`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/e1febd35ad85208e8a296e1828fb7fbdee29f672) | [`c1088a72`](https://github.com/casama233/astrbot_plugin_rollpig/commit/c1088a727a9e00f74e287a4d52e3ae80f21c4c8b) | **RollPig Plus-derived protocol/design; MIT-derived paths must retain notice** | The combination of EX 1–5, sparse levels, `image` / `description` / `analysis`, per-field inheritance, `pig_ex_variants.json`, `variant_images`, staging/validation and same-version optional-resource completion is too specific to describe as wholly independent. Current implementation is not assumed line-for-line identical; path-level derivation remains under audit. |
| Roast reservation / free firewood participation | [`76b25bbb`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/76b25bbb7fa34504f336dc956116da7350ec4357) | [`1e2bad06`](https://github.com/casama233/astrbot_plugin_rollpig/commit/1e2bad06d7dc3476f1b60b16268faf32d2a3ea03) | **Design/state-machine reference; code-level derivation still being checked** | Both use first participant as chef, chef pays the normal cost, later participants join free, participant de-duplication, default 12 participants, trigger after the target's same-day draw/display and 60/30/10 settlement. Sampled current implementations differ substantially in storage and delivery structure, so this is not presently classified as a line-by-line copy. |
| Daily report awards | RollPig Plus initial independent repo history including [`22b5357c`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/22b5357c3b6ae87fa5b048304cfab6913d83dda1) | [`1440a759`](https://github.com/casama233/astrbot_plugin_rollpig/commit/1440a759bf6506057592a112c92873accc729ebf) | **User-facing copy/statistical-design reference** | The four display labels `烧烤狂人` / `最惨食材` / `逃脱大师` / `反噬之王` match exactly. Sampled current aggregation code differs in details, so the exact labels/source are credited without claiming identical implementations. |
| Oven refill | [`1dcc8392`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/1dcc8392a463f4bfe7f339ede172417b4434bc7d), merged in [`36d0687c`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/36d0687c7fb26e087e8baea44afa2a960c677d34) | event lifecycle introduced in [`cb3d4099`](https://github.com/casama233/astrbot_plugin_rollpig/commit/cb3d4099a1abf120a38371a4dea3c2d5d9dc7474), later implementation evolved further | **At minimum design/event-naming reference** | The same gameplay name and `oven_refill_started/supported/succeeded/failed` lifecycle appeared shortly after RollPig Plus. The present implementation needs a separate path-level comparison before classifying implementation derivation. |
| Resource-sync hardening | RollPig Plus `resource_manager.py` history | local updater/resource-source hardening history | **Implementation/design reference under path-level audit** | The reported overlap includes download budgets, count/size limits, safe manifest paths, rejection of absolute/parent/backslash/URL paths, size/SHA checks, staging, total-budget tracking, old/new directory activation and conditional rollback. These controls are individually common security practices, but the combined flow and timing justify explicit source review rather than an independence claim. |
| PigHub fallback behavior | RollPig Plus [`b537cbb7`](https://github.com/Felis2026/nonebot-plugin-rollpig-plus/commit/b537cbb7d11bad2afe2649c18bbc873608f860df) and later PigHub client history | local PigHub client history | **Reference/implementation overlap under audit** | Use of PigHub itself is not proprietary. The audit concerns the more specific fallback order (`images?sort=2&limit=200` → `images?sort=2` → `all-images`) plus related cache/fallback behavior. |
| Generic roast probabilities / random target selection | mixed RollPig lineage | mixed RollPig lineage | **Not sufficient on its own to establish derivation** | A shared 60/30/10 rule or selecting an eligible random group target is documented for completeness, but these isolated gameplay rules are not treated as proof of code copying without stronger path-level evidence. |

The initial sampled comparison shows that some current implementations are structurally different even where feature/state-machine correspondence is strong. The remediation therefore preserves attribution now while continuing to distinguish concrete code derivation, design/reference reuse and independent implementation on a file-by-file basis.

## Resource distribution rule while audit is incomplete

Resources must not be assumed redistributable merely because related source code is MIT licensed. Any image, prose pack, catalog entry or other asset whose provenance or redistribution permission cannot be verified should be withheld from public distribution until the source and permission are confirmed.

Public-source submissions created independently by users should retain their own contributor/source metadata where available.

## Maintainer commitment

The maintainer will:

- keep upstream credits visible in README/license documentation;
- preserve required MIT copyright and permission notices;
- avoid claiming exclusive authorship over upstream-derived work;
- distinguish software licensing from artwork/content redistribution rights;
- remove or stop distributing material whose redistribution rights cannot be established;
- record material provenance corrections in public commits/PRs where possible;
- provide a contactable public path for future attribution reports.

Repository Issues are currently disabled and should be re-enabled as part of this remediation. Until that setting is changed, attribution concerns may be raised through a pull request or the public [AstrBotDevs/AstrBot#9687](https://github.com/AstrBotDevs/AstrBot/issues/9687) thread.

If you believe a file, feature, resource or text is missing attribution, please report the exact path or item so it can be reviewed and corrected.
