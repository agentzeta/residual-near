# X demo post

Rules: a public post on X, saying you built it at NEAR HACKATHON, tagging @NEARProtocol and #NEARHackathon, with a video or screenshots. The organizers' tips: lead with the user's problem, show one complete moment from action to result, say what NEAR concretely does in the product, link the demo and repo, and ask a specific question. @NearLegion and @NearBuilders are optional extra tags.

## Main post (attach residual-demo.mp4)

> Adding a post-quantum key to a NEAR account doesn't retire the old classical key. It still has full control.
>
> Residual, built at NEAR HACKATHON, checks any account live from mainnet and samples recent signers.
>
> Try it: https://agentzeta.github.io/residual-near/
>
> @NEARProtocol #NEARHackathon

(272 of 280 characters once X shortens the link.)

## Reply 1: the result and the repository

If the snapshot has run:

> Today's snapshot, block [HEIGHT]: of [N] recently active signers, [X] have a PQ key and [Y] still hold classical full access. Raw RPC data and digests are published; anyone can rerun it.
>
> Code (MIT, read-only, Lean-checked classifier): https://github.com/agentzeta/residual-near

If it has not:

> Open source, read-only, and the classifier is checked against a Lean 4 model: https://github.com/agentzeta/residual-near

Zero PQ adopters in a sample is a real result: ML-DSA keys are weeks old. Say so rather than leaving it out.

## Reply 2: the question

> Question for NEAR wallet teams: once ML-DSA signing lands in your wallet, would you show users "classical key still live" with a one-tap path to retire it? What would you need from a tool like this?
