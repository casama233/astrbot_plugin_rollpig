# Derived public asset replacements — 2026-08-26

This note records the provenance decision for two existing RollPig IDs whose local production images are intended to replace the older bundled images. The resource IDs and catalog count do not change.

The exact replacement PNGs are not yet committed on this branch. Until those binary blobs are added and their SHA-256 values are verified by CI, this branch is staging-only and must not be merged as a completed publication change.

## `roasted-pig`

- Decision: approved public replacement.
- Role: optimized replacement of the earlier Bear/Meg asset.
- Earlier source: `Bearlele/nonebot-plugin-rollpig`, `nonebot_plugin_rollpig/resource/image/roasted-pig.png`.
- Earlier source SHA-256: `2ac2151d9b258553f47b76a494ac37fb0fcb7c555d21c648fda15c83f540c6b1`.
- Replacement SHA-256: `f096f63e77e109efc0cdc29cfa85aac121336ced66082a4fd84745f96ad6d547`.
- Rights basis: derivative of the earlier MIT-licensed project-lineage asset.
- Attribution retained: Bear_lele / MegSopern project lineage.
- Transformation: image optimization; the production comparison classified it as a very likely optimized copy of the Bear/Meg baseline.

## `pigsleep`

- Decision: approved public derived rework.
- Role: substantial redraw of the earlier Bear/Meg asset under the same existing ID.
- Earlier source: `Bearlele/nonebot-plugin-rollpig`, `nonebot_plugin_rollpig/resource/image/pigsleep.png`.
- Earlier source SHA-256: `6e037397c3a88d675313dc3962f9b8e3c8714ba5a5d94255406a3dd5d202ffc3`.
- Replacement SHA-256: `5f38caab39ecdbe23be25d6df9e9ad24538779de727a9563052aa93d1a0cdeb4`.
- Rights basis: derivative of the earlier MIT-licensed project-lineage asset.
- Attribution retained: Bear_lele / MegSopern project lineage.
- Transformation: substantial redraw / visual redesign.
- Derivation confirmation: on 2026-08-26 the project operator confirmed that the replacement was made from the Bear/Meg MIT `pigsleep` asset.

## Explicit non-approval: `papa-pig`

`papa-pig` is not part of this approval. The current evidence says the image was downloaded from an external source and later uploaded locally. Wide circulation as a meme does not establish public-domain status or a redistribution license, so it remains withheld from public redistribution pending stronger rights evidence.

## Merge gate

Before this work may be considered complete:

1. commit the exact `roasted-pig.png` whose SHA-256 is `f096f63e...6d547`;
2. commit the exact `pigsleep.png` whose SHA-256 is `5f38caab...deb4`;
3. add a build/CI check that the committed image hashes match the approved provenance records;
4. ensure the resource-source builder carries the machine-readable provenance record into the generated public-source artifact;
5. run the normal resource-source and test workflows successfully.

No PigHub-only item is approved by this note, and no gameplay behavior is changed.
