# Resource provenance audit

Last updated: 2026-08-19

This document records the resource-focused portion of the remediation started after the attribution concerns in [AstrBotDevs/AstrBot#9687](https://github.com/AstrBotDevs/AstrBot/issues/9687).

It is evidence/provenance documentation, **not a blanket license grant** for artwork, prose, catalog data or other resources.

## Current publication rule

The project now follows a fail-closed resource rule:

> A resource that cannot be tied to a documented source and redistribution basis is withheld from public redistribution until that provenance is established.

Software licensing and resource licensing are reviewed separately. The fact that code is MIT-licensed does not by itself grant rights to artwork, prose, community submissions or mirrored resource packs.

## Findings and remediation

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

For these baseline assets, the repository preserves the earlier project-lineage attribution rather than incorrectly describing them as newly copied from RollPig Plus.

This establishes parent lineage for the checked blobs; it does **not** independently establish the original artwork license for every historical asset.

### 2. The bundled `resource/pig.json` base catalog is also parent-lineage content

Checked opening entries in this repository's bundled `resource/pig.json` match the direct MegSopern parent copy, including the rewritten `human`, `pig` and `black-pig` descriptions/analysis.

The corresponding current `Felis2026/nonebot-plugin-rollpig-plus` catalog uses different prose for those checked entries. Therefore the bundled base catalog is not being described as a wholesale copy of the current Felis catalog.

This is a sampled lineage finding and does not excuse later individual additions from item-level review.

### 3. Bundled authored EX copy has been quarantined

The following authored EX resources were previously identified as later material requiring separate provenance review:

- `resource/pig_ex_variants.json`;
- `resource/ex_curated/*.json`.

As part of the 2026-08-19 remediation, those authored bundled files are removed from the current publication tree pending item-level provenance/permission review.

The EX mechanism itself is retained. When no explicit cloud/bundled authoring document is available, the plugin uses its existing deterministic five-level baseline derived from the active base catalog. This preserves EX behavior without redistributing the quarantined authored prose.

Tests now enforce both conditions:

1. authored bundled EX files are absent; and
2. the deterministic baseline still produces complete EX1-EX5 presentation data for the bundled catalog.

### 4. Bundled roast-copy has been replaced rather than presumed cleared

The previous `resource/roast_copy.json` was subject only to limited negative exact-text sampling. That sampling was not sufficient to establish independent provenance for the complete pack.

Instead of treating the old pack as cleared, the 2026-08-19 remediation replaces it with a newly authored bundled roast-copy pack. The replacement is intentionally a fresh set of dish names and lines rather than a phrase-by-phrase edit of the old pack.

The production provenance-safe restoration profile does not publish a remote roast-copy pack at all. Clients may use the newly authored bundled fallback until a separately audited remote text pack is intentionally introduced.

### 5. Historical Felis compatibility-floor redistribution is confirmed and now fail-closed

A historical compatibility path used the frozen resource snapshot:

- repository: `Felis2026/rollpig-resources`;
- commit: `17ac1586a91c33995883803a55e2f755047f6e1f`;
- resource version: `2026-08-10.1`;
- fixed `pig.json` SHA-256: `687a491e541869cf1ef4f495e9189cf358a0d68655d1f780395a482113bc8be8`;
- sentinels: `miku-pig`, `wechat-pig`, `duke-pig`.

That mechanism did more than preserve IDs: for records missing from the AstrBot catalog it could copy the record and corresponding image from the frozen compatibility snapshot into a merged public catalog. It is therefore a direct resource-redistribution provenance issue, not merely a software-attribution issue.

The remediation now disables that path in both publication layers:

- this public repository's Resource Source GitHub Actions workflow no longer checks out the Felis resource repository, no longer runs a compatibility-floor restore, no longer requires compatibility sentinels, and no longer uploads a merged compatibility catalog;
- `scripts/prepare_resource_catalog.py` retains the historical metadata for forensic reproducibility but rejects the historical Felis compatibility spec by default and its CLI cannot publish it;
- the private production service separately keeps its retained compatibility migration fail-closed for publishing, with any explicit bypass reserved for isolated audit/reproduction only.

Historical identifiers are intentionally retained in audit code/documentation so the remediation can be reproduced. Removing the evidence would make provenance review harder and is not a substitute for stopping redistribution.

### 6. Production catalog was audited directly and remains offline

Git repository state alone was insufficient because the production review/catalog storage is outside the service code release tree. A direct production audit was therefore performed while public serving was disabled.

The Phase 3 offline result supplied by the production operator on 2026-08-19 was:

- production canonical records: **204**;
- provenance allow set: **157**;
- quarantine set: **47**;
- allow/quarantine overlap: **0**;
- uncovered canonical IDs: **0**;
- foreign IDs in the classification: **0**;
- the 47 quarantined records and their base images were removed from the offline candidate;
- resulting clean candidate: **157** records;
- `PROVENANCE.json`: **157** entries;
- `NOTICE.md` and `LICENSES/` were added to the candidate;
- a formal offline builder validation completed successfully.

Crucially, that validation did **not** constitute republication. At the end of the phase the service remained inactive, the public resource directory remained inaccessible, and the public HTTP endpoint returned `403`.

The earlier full builder also materialized EX/roast-copy extended resources, so that validation alone is not used as the final restoration artifact. The private production service now has a dedicated `provenance-safe-base-only` builder whose restoration profile requires the attribution bundle and is structurally incapable of including authored EX, EX images or roast-copy resources.

The production source must remain offline until a final base-only candidate is rebuilt and checked with that profile.

## Resource remediation rules

1. **Do not delete inherited baseline assets solely because the same blob also exists in RollPig Plus.** Check whether the blob predates fork divergence or exists in Bearlele/MegSopern lineage first.
2. **Do not treat MIT code licensing as artwork/prose licensing.** Resource rights are reviewed independently.
3. **For Felis-exclusive material that was copied or adapted**, preserve applicable source/license notices when redistribution is actually covered; otherwise withhold it until permission is established.
4. **For unknown-source images/text**, withhold them from public distribution until provenance is documented.
5. **For independently submitted public-source content**, retain contributor/source metadata where available.
6. **Record removals and provenance corrections publicly** in remediation changes where practical.
7. **Do not use an external compatibility snapshot as an automatic public source without documented redistribution permission for the copied material.**
8. **Do not treat a successful technical build as a provenance decision.** A restoration artifact must also satisfy the provenance-safe publication profile.

## Audit status

- Baseline parent image lineage: **sampled and confirmed**.
- Base `pig.json` lineage: **sampled and confirmed as MegSopern-parent text for checked entries**.
- RollPig Plus-derived feature/protocol attribution: **documented in `ATTRIBUTION.md`; path-level audit ongoing**.
- Bundled authored EX copy: **quarantined from current publication tree; deterministic baseline retained**.
- Bundled roast-copy: **historical pack no longer presumed cleared; replaced with newly authored fallback**.
- Felis compatibility-floor mechanism: **confirmed and disabled for automatic/public publishing; retained audit-only metadata is fail-closed**.
- Production base catalog/images: **direct Phase 3 classification completed: 157 allow / 47 quarantine; no republication yet**.
- Final production restoration artifact: **pending rebuild with the provenance-safe base-only profile; public source remains offline until that check passes**.
