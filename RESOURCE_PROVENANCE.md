# Resource provenance audit

Last updated: 2026-08-19

This document records the resource-focused portion of the remediation started after the attribution concerns in [AstrBotDevs/AstrBot#9687](https://github.com/AstrBotDevs/AstrBot/issues/9687).

It is evidence/provenance documentation, **not a blanket license grant** for artwork or text.

## Why this is separate from the software license

The repository's MIT software license covers software distributed under that license. Images, fonts, prose, catalog data and other content can have different origins and licensing conditions. A resource must not be treated as freely redistributable merely because the code loading it is MIT-licensed.

## Findings so far

### 1. Baseline pig images are inherited from the direct AstrBot parent

A large set of identical pig image files appears in both this repository and `Felis2026/nonebot-plugin-rollpig-plus`. Git blob identity by itself does not show that those files were copied from Felis, because the same blobs already exist in the direct GitHub parent [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig).

Verified examples include:

| File | Git blob SHA | Present in MegSopern parent | Present here | Present in Felis RollPig Plus |
| --- | --- | --- | --- | --- |
| `abstract-pig.png` | `675427ea906fc5f0933ec9caccdee21bd642317d` | yes | yes | yes |
| `alien-pig.png` | `e96d75b5a15738e36fdc4729b40ab635260e4077` | yes | yes | yes |
| `android-pig.png` | `6e38fe9d54aeff6e56df74b89ef20fff985068df` | yes | yes | yes |
| `antibacterial-pig.png` | `690cd0e5c7bd6085cd4f7552974d299ee16a1378` | yes | yes | yes |
| `apple-of-eye-pig.png` | `2e93cf2dd7829b3015fbb0264d2a327999aa5c95` | yes | yes | yes |
| `apple-pig.png` | `237fbb98aa54158ce7cca6cb528f283c10f6d83a` | yes | yes | yes |
| `bacon.png` | `155b720d934f610fb9a1789508d50167449ee4d2` | yes | yes | yes |
| `bamboo-pig.png` | `ab063ac887fd9e924143ec93e5bc90efc471636d` | yes | yes | yes |
| `bandage-pig.png` | `ad507b7946d46d762df3ca1317f0cbdbe0e94724` | yes | yes | yes |
| `big-lazy-pig.png` | `109af6169eb720f1094d8bbba61f2038057df3cd` | yes | yes | not needed for origin determination |
| `black-pig.png` | `4692848076222ede43279907759e7574482cbbba` | yes | yes | not needed for origin determination |
| `black-white-pig.png` | `4c0d9c28c01ab422047245b47289701459515502` | yes | yes | not needed for origin determination |

For these baseline assets, the repository should preserve the earlier project-lineage attribution rather than incorrectly describing them as newly copied from RollPig Plus.

This finding does **not** establish the original artwork license by itself; it establishes that the files were already inherited through this repository's direct parent lineage.

### 2. The bundled `resource/pig.json` copy is also parent-lineage content

The opening entries in this repository's `resource/pig.json` match the direct MegSopern parent copy, including the rewritten `human`, `pig` and `black-pig` descriptions/analysis.

The corresponding current `Felis2026/nonebot-plugin-rollpig-plus` `pig.json` uses different prose for those entries. Therefore, the current bundled base catalog should not be described as having been copied wholesale from the current Felis catalog.

This does not rule out later individual catalog/resource overlaps; those need item-level review.

### 3. Later resource additions require separate review

The following are not covered by the baseline-parent finding and remain in the audit scope:

- `resource/pig_ex_variants.json`;
- `resource/ex_curated/*.json`;
- `resource/roast_copy.json`;
- any remotely published catalog entries that are not present in the inherited parent resource tree;
- any remotely published images obtained after the fork diverged;
- any mirrored RollPig Plus resource pack, if present in production/public-source storage.

#### `resource/roast_copy.json` sample check

The local pack contains later project-specific copy such as `可爱可以加葱，不能减刑` and `成长的尽头不是毕业，是更大的烤盘`. Sample searches of the current public Felis repository did not return those exact phrases.

That is only a limited negative check. It is **not** proof that the whole pack is independently authored, and it does not replace a complete provenance review.

### 4. The production compatibility floor explicitly uses a frozen Felis resource snapshot

The private production service contains a retained compatibility migration whose `LEGACY_COMPATIBILITY` source is:

- repository: `Felis2026/rollpig-resources`;
- commit: `17ac1586a91c33995883803a55e2f755047f6e1f`;
- resource version: `2026-08-10.1`;
- fixed `pig.json` SHA-256: `687a491e541869cf1ef4f495e9189cf358a0d68655d1f780395a482113bc8be8`;
- sentinels: `miku-pig`, `wechat-pig`, `duke-pig`.

The migration is not merely an ID-preservation list. For IDs missing from the current AstrBot catalog, it takes the record from that frozen Felis snapshot and copies the corresponding image from the compatibility snapshot into the merged catalog. Current AstrBot records/images win only when the same ID already exists.

This is therefore a **direct resource redistribution provenance issue** and must not be treated as only a feature-design or MIT-code attribution issue.

At the frozen commit above, the repository root did not contain a `LICENSE` or `RESOURCES-LICENSE.md`. The current `Felis2026/rollpig-resources` repository now explicitly separates software from resources: its current license says Felis-original images/text are not covered by the MIT software license and points to separate resource terms that include restrictions on bulk mirroring/re-hosting and attribution requirements.

This audit does not assume that today's resource terms retroactively change any permission that may or may not have existed at the frozen commit. It records the narrower and safer conclusion: **the current project does not yet have documented redistribution permission for every Felis-snapshot record/image restored by the compatibility-floor migration, so those restored items must be treated as unverified until provenance/permission is established.**

Required remediation for this compatibility floor:

1. identify the exact `restored_ids` produced when the migration was run against production;
2. for each restored ID, determine whether its record/image came from Bearlele/PigHub/community material or Felis-original material and retain the applicable source notice;
3. stop relying on the Felis snapshot as an automatic future compatibility source unless redistribution permission is documented;
4. withhold any Felis-original or otherwise unverified restored resources from the public mirror until permission is established;
5. retain evidence of the frozen source commit and the remediation decision rather than deleting history.

### 5. Production/public-source storage is a separate audit target

The private `casama233/rollpig-public-source-service` repository documents that production review state and the public catalog/published resources are stored outside the code release tree. Therefore a clean Git repository comparison alone cannot establish what the public `curryudon.top` resource endpoint is currently distributing.

The production catalog and image store must be audited directly before claiming that all publicly served resources have verified provenance.

Until that check is complete, any remotely published item whose source or redistribution permission cannot be established should be withheld from public distribution.

## Resource remediation rules

1. **Do not delete inherited baseline assets solely because the same blob also exists in RollPig Plus.** Check whether the blob predates the fork divergence or exists in Bearlele/MegSopern lineage first.
2. **Do not treat MIT code licensing as artwork/prose licensing.** Resource rights must be checked independently.
3. **For Felis-exclusive material that was copied or adapted**, preserve the applicable source/license notice when the material is actually covered by that license; otherwise stop redistribution until permission is established.
4. **For unknown-source images/text**, withhold them from public distribution until provenance is documented.
5. **For independently submitted public-source content**, retain contributor/source metadata where available.
6. **Record removals or provenance corrections publicly** in the remediation PR where practical.
7. **Do not use an external compatibility snapshot as a future automatic source without documented redistribution permission for the material being copied into the mirror.**

## Audit status

- Baseline parent image lineage: **sampled and confirmed**.
- Base `pig.json` lineage: **sampled and confirmed as MegSopern-parent text for checked entries**.
- RollPig Plus-derived feature/protocol attribution: **documented in `ATTRIBUTION.md`; path-level audit ongoing**.
- `roast_copy.json`: **sample negative exact-text checks complete; full review pending**.
- EX curated copy/resources: **pending item-level review**.
- Felis compatibility-floor mechanism: **confirmed; restored-ID provenance/permission audit required**.
- Production `curryudon.top` catalog/images: **not established by Git repository state; direct production audit required**.
