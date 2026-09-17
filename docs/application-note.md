# Application companion: SourceCheck

Drafts for Shrey Patel to review and personalize. AI assistance was used for the investigation and implementation. These answers make no claims about production usage, past work, or personal decisions that have not been verified. Understand and own the implementation before submitting.

## Submission note

I built SourceCheck after investigating a real OpenAlex record whose primary DOI and authors described one paper while its title described another. The attached DOI sources contained three distinct publication families. I checked the source claims against DataCite and the publisher, preserved the raw responses, and built a tool that makes this conflict reproducible.

You can enter a DOI or work ID, inspect the registered titles and creator evidence, and export a review packet. The Python CLI and browser implementation use free public metadata services. A targeted follow-up check found five title disagreements across 30 records; I report that as a bounded investigation, not an error-rate estimate.

The important decision was to avoid a title-only “fix” that would leave unrelated sources attached. This is a working detection and evidence-assembly tool, not a claim to have repaired OpenAlex. I used AI assistance and documented the evidence, tests, assumptions, and limits.

[Live tool](https://openalex-repair-desk.vercel.app/) · [GitHub](https://github.com/Shreyp087/OpenAlex) · [Evidence report](https://openalex-repair-desk.vercel.app/downloads/SourceCheck-Evidence-Report.pdf)

## A 90-second demonstration

**0:00-0:20 - Show the contradiction.** Open the captured case for W4385245566. Point to the primary DOI, the OpenAlex title, and the different title registered for that DOI. “These are preserved public responses, not errors I injected.”

**0:20-0:40 - Explain why the repair is not obvious.** Inspect the DOI source families. “Nine author ORCIDs match the MizAR paper, while the title belongs to another attached source. The three Zenodo records have legitimate version relations. Multiple DOIs alone are not the problem.”

**0:40-1:00 - Run the tool.** Use the explicit live check on the same ID or another DOI. “This fetches current public metadata and reports agreement, a review signal, or insufficient evidence. It does not overwrite scholarly records.” If a service is unavailable or the record has changed, show that outcome honestly.

**1:00-1:15 - Show the evidence handoff.** Download the report and point to the receipt manifest and offline verifier. “Someone else can reproduce the captured result without trusting the UI or repeating a network request.”

**1:15-1:30 - State the limit.** “I checked a targeted set of 30 neighboring records and found five title disagreements. That is not a population error rate. My next step with your team would be to trace a confirmed case through the internal source-association process.”

## Why do you want to work here?

OpenAlex makes research usable beyond the institutions and people who can pay for closed databases. A paper I co-authored is already in the library, so that mission is personal to me.

The engineering work appeals to me for the same reason: a small decision about messy metadata can affect how a researcher is represented or what an agent cites. While building this application artifact, I found a record that combined conflicting source claims. The interesting part was working out what the evidence justified, what needed review, and how another engineer could reproduce it.

I want the ownership described in this role: understand a user's problem, trace it into the data, build a useful change with agents, test it, and explain the result clearly. SourceCheck is a concrete example of the kind of problem I would enjoy working on with your team.

## What will you do in your first week?

Start with the support queue and an engineer who knows the ingestion path. I would walk through a few recent reports, learn how source records become work records, and understand the team's deployment and rollback process.

I would bring SourceCheck's captured case as something to investigate, not arrive assuming I know the production cause or that the team lacks a tool. With the team's context, I would pick one small recurring failure, preserve a minimal reproduction, and identify the right place for a check or fix.

I would use agents to help implement it, while owning the evidence, diff review, and validation. By Friday, my target would be one verified improvement shipped through the existing process, a regression check, and a clear response to the affected user. The actual scope would follow what the team needs most.

## What's the coolest thing you've ever built?

The project I would like to show you is SourceCheck, which I built with AI assistance for this application.

It began as a metadata investigation. One public OpenAlex record had the DOI and nine authors of “MizAR 60 for Mizar 50,” but its title belonged to another paper. Looking at the attached locations revealed three distinct publication families. That changed the implementation: a title replacement would conceal part of the issue, so the tool needed to expose the source conflict and produce a review packet.

The result is a working Python CLI and browser audit, backed by preserved HTTP responses, checksums, offline reproduction, and tests for uncertainty and failure cases. It uses free services and makes no upstream changes. The part I find most compelling is turning a surprising public record into something another engineer can inspect and act on, while keeping the boundary between evidence and hypothesis clear.

## Submission boundaries

- Say “detected and documented a source conflict,” not “fixed OpenAlex.”
- Say “five title disagreements in a targeted 30-record cohort,” not “OpenAlex has a 16.7% error rate.”
- The shared `Cites` identifier is an investigative lead; the internal cause has not been proven.
- Preserve the AI-assistance disclosure. Add personal anecdotes or prior project claims only if you can substantiate them.

## Links

- [Live SourceCheck](https://openalex-repair-desk.vercel.app/)
- [Public repository](https://github.com/Shreyp087/OpenAlex)
- [Evidence PDF](https://openalex-repair-desk.vercel.app/downloads/SourceCheck-Evidence-Report.pdf)
- [Full technical documentation](REAL-PROBLEM.md)
- [Portfolio](https://shrey-portforlio.netlify.app/)
- [Shrey's co-authored paper](https://doi.org/10.1007/s10163-025-02248-x)
