# Application companion

These are drafts for Shrey Patel to review and personalize. The artifact was generated with AI assistance for this application. Before submitting, run it, inspect its decisions, and change any sentence that does not reflect your own experience or judgment.

## Short accompaniment

My research is in this library. I made something small to help keep its records trustworthy.

Repair Desk is an independent, runnable prototype built around a paper I co-authored that is indexed in OpenAlex. It takes a synthetic support case through preserved source evidence, a local pipeline replay, explicit decision gates, and an executable regression. The four cases include a dropped affiliation, conflicting author identifiers, sparse metadata that should be left alone, and an ingestion replay that should not duplicate a work.

My proposal is simple: every resolved ticket should leave behind a regression test. OpenAlex already has agent-assisted curation; this explores a small engineering companion to that workflow. The faults are deliberately injected, the live record is not being accused of an error, and no correction is sent to OpenAlex.

I used AI assistance to build the prototype. I would welcome a conversation about the evidence gates, the limits of the evaluation, and what I would change after seeing real tickets.

## A 90-second demonstration

**0:00-0:15 - Make it personal.** Open the casebook and follow the source-record link. “This is a paper I co-authored. It makes the mission concrete for me: a library is useful when a researcher can trust how their work is represented.”

**0:15-0:35 - Show one diagnosis.** Select the affiliation case. Point to the fixture label, raw input, and before/after evidence. “I injected a local transformation fault. The replay distinguishes what the source supplied from what a transform lost.”

**0:35-0:55 - Show restraint.** Open the conflicting-ORCID case, then sparse metadata. “Conflicting identifiers need review. A missing field can be an upstream gap. A useful system needs a way to stop without inventing data.”

**0:55-1:10 - Show a backend property.** Open the DOI replay case. “Different delivery formats should not create a second work. The replay tests the materialization key and preserves the delivered evidence.”

**1:10-1:25 - Show the handoff.** Open the regression/evidence bundle and support reply. “The next engineer gets a reproducible case, and the user gets an explanation that matches what we actually know.”

**1:25-1:30 - State the next step.** “I would test this approach against a small, reviewed sample of real tickets before expanding it.”

## Why do you want to work here?

OpenAlex connects two things I care about: open research and systems whose decisions can be inspected. A paper I co-authored is already in the library, so the mission is personal as well as technical.

My portfolio keeps returning to evidence and uncertainty: Prompt Firewall exposes a detector's decision, Aegis Desk treats evidence and uncertainty as part of triage, and our team’s AI Incident Observatory makes coverage limits visible. I want to bring that instinct to messy scholarly data, where a plausible-looking match can quietly misrepresent a researcher.

The ownership in this role is especially appealing. I want to follow a problem from a user's report into the data, through a fix and its regression test, and back to a clear reply. I made Repair Desk with AI assistance to make that interest concrete.

## What will you do in your first week?

Start with the support queue and the people who answer it. I would ask an engineer to walk me through a few recent data-quality tickets: one straightforward correction, one ambiguous report, and one that revealed a pipeline issue. I would trace one of them from the harvested record to the API response and learn the team's deployment and rollback habits.

Then I would pick the smallest recurring failure we agree is worth fixing, preserve a minimal reproduction, and use agents to help implement the change. My job would be to define the evidence, inspect the diff, test the failure and a nearby negative control, and ship through the existing process.

By Friday, my target would be one small verified improvement, a regression that survives me, and a useful reply to the person who found the problem. The exact fix would follow the evidence; I would not arrive assuming my prototype is the team's missing tool.

## What's the coolest thing you've ever built?

**Draft centered on an established portfolio project. Personalize with a concrete technical decision you can defend.**

Prompt Firewall is a project I would be excited to discuss. It is a maintained research prototype that treats a prompt draft as something to quarantine and inspect before it is trusted. What interests me is the boundary: the system should make a decision you can trace, and its uncertainty should remain visible.

That same idea motivated this application artifact. I used AI assistance to create Repair Desk around my own OpenAlex-indexed paper: preserve the input, reproduce a failure, require evidence before changing a record, and turn the diagnosis into a regression. It is deliberately a small local prototype. The part I find compelling is the connection between a user's complaint and a test that protects the next user.

Before submitting, add one specific Prompt Firewall example: the failure you observed, the design choice you personally made, and the tradeoff you accepted. Do not add production usage or performance claims that you cannot substantiate.

## Links

- [Portfolio](https://shrey-portforlio.netlify.app/)
- [Paper in OpenAlex](https://openalex.org/W4410234973)
- [Published paper](https://doi.org/10.1007/s10163-025-02248-x)
- [OpenAlex's existing correction workflow](https://help.openalex.org/access/fixing-errors/)
