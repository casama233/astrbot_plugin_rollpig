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
- keep a contactable public issue/discussion path available for future attribution reports.

If you believe a file, feature, resource or text is missing attribution, please report the exact path or item so it can be reviewed and corrected.
