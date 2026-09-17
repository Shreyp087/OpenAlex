# Discovery log: title and source divergence in OpenAlex

This log records observations from public services on 2026-09-17. It does not assert an upstream root cause or claim to repair OpenAlex itself. Raw responses and their SHA-256 hashes are in `data/evidence/title-divergence/manifest.json`.

## How the first case was found

[OpenAlex issue #7](https://github.com/ourresearch/OpenAlex/issues/7) describes missing references and associates work `W4385245566` with “Attention Is All You Need.” That historical report was treated as a lead, not as current truth. The current OpenAlex response for that ID instead has primary DOI `10.4230/lipics.itp.2023.19` and a different title. Both the [ID lookup](https://api.openalex.org/works/W4385245566) and [DOI lookup](https://api.openalex.org/works/doi:10.4230/lipics.itp.2023.19) returned the same work ID and the title “Exploiting Generative AI to Scale up Intelligent Tutoring Systems.”

The [DataCite DOI registration](https://api.datacite.org/dois/10.4230/lipics.itp.2023.19) and [publisher page](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2023.19) identify this DOI as “MizAR 60 for Mizar 50.” The nine listed names in the OpenAlex authorships match the registry creators in order. However, the OpenAlex locations contain additional DOI-bearing sources associated with different titles. Therefore this is not a safe automatic title-only replacement: the entire source bundle needs review. The tool should surface this collision and create a traceable review packet.

The first four receipts were captured at 2026-09-17 16:50:39–42 UTC. Exact times and hashes are in the manifest. These are original response bodies, not synthetic mutations.

## Independent neighboring check

The adjacent DOI [10.4230/lipics.itp.2023.18](https://api.openalex.org/works/doi:10.4230/lipics.itp.2023.18) returns OpenAlex ID `W4298857588` with the title “Robust Mean Estimation by All Means (Short Paper).” Both its [DataCite record](https://api.datacite.org/dois/10.4230/lipics.itp.2023.18) and [publisher page](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2023.18) instead identify “Semantic Foundations of Higher-Order Probabilistic Programs in Isabelle/HOL.” The OpenAlex authorships and registry creators also disagree. This is a second independently retrievable divergence.

The following DOI, suffix 20, agrees on title and ordered names between OpenAlex and DataCite. Shrey Patel’s paper (`10.1007/s10163-025-02248-x`) agrees on title between OpenAlex and Crossref. Agreement on these fields is not a claim that the whole record is correct.

## A reported issue that no longer reproduces

[Issue #12](https://github.com/ourresearch/OpenAlex/issues/12) reports IEEE DOI `10.1109/lmwt.2025.3613530` as missing. During this investigation, its DOI lookup returned HTTP 200, OpenAlex ID `W7084769202`, and the same title as Crossref. We therefore do not label it currently missing, despite the GitHub issue still being open.

## Sampling boundary

After finding the two adjacent disagreements, the investigation was expanded to the first 30 numbered DOI suffixes (1–30) of [LIPIcs volume 268, ITP 2023](https://drops.dagstuhl.de/entities/volume/LIPIcs-volume-268). The publisher volume lists numbered contributions 1–38 plus front matter. This is a targeted contiguous cohort chosen after discovery of a problem in that volume. It is not random, does not estimate OpenAlex-wide error prevalence, and cannot measure detector precision or recall. `summary.json` contains derived comparisons and counts; the raw receipt manifest is authoritative for capture times and payload integrity.

## Limits on interpretation

A title discrepancy can arise from a legitimate alternate title, a registry update, or an upstream merge error. A DOI identifies a work, but having that DOI in one location does not by itself prove a merged source bundle is correct. DataCite and the publisher are corroborating sources and may share an upstream metadata feed; they are not statistically independent witnesses. No causal pipeline claim is made from API output alone. No correction, support message, or merge was submitted to OpenAlex.

## Captured cohort result

All 30 OpenAlex and 30 DataCite singleton lookups ultimately returned HTTP 200. Five transient failures were retried once; the failed-attempt metadata is retained in the manifest. After Unicode NFKC normalization, case folding, and collapsing punctuation/whitespace into word boundaries, 25 DOI pairs agreed on the title and five did not. The disagreements are suffixes 13, 17, 18, 19, and 26. These counts describe this captured, targeted cohort only. Eleven ordered creator-name lists differ literally after normalization; names can be represented in different formats, so that number is not a count of author-attribution errors.

The evidence set contains 70 successful raw-response receipts, each with its URL, HTTP status, retrieval timestamp, byte length, and SHA-256 checksum. The cohort used no API keys and made no write requests.
