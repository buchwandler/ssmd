---
ssmd_version: "0.9"
title: SSMD 0.9 Feature Example
pause_defaults:
  enabled: true
  paragraph: 450ms
---

# Text and Emphasis

Plain text can include punctuation such as &.

_moderate emphasis_, **strong emphasis**, and ~~reduced emphasis~~.

# Breaks, Language, and Voice

A sentence break ...s, a word break ...w, and a timed pause ...500ms.

I saw [Guardians of the Galaxy]{lang="en-GB"} in the cinema. [Bonjour]{lang="fr-FR"}
tout le monde!

:::{lang="en-US"} Welcome to the show! :::

[Hello there.]{voice="host"} [Bonjour]{gender="female" voice="guest"
voice-languages="fr-FR"}

:::{voice="host" voice-languages="en-US"} Welcome to the show! I'm the host. :::
:::{voice="guest" voice-languages="en-US"} Thanks for having me. :::

# Marks and Paragraphs

I always wanted a @animal cat as a pet. Click @continue to continue.

First prepare the ingredients. Wash them carefully.

Lastly mix them all together.

Don't forget to do the dishes after!

# Headings and Pronunciation

## A section heading

### A smaller heading

[tomato]{ph="təˈmeɪtoʊ"} is pronounced with three syllables. The German word
[dich]{ph="dɪç"} has a sound not found in English.

# Prosody

[Softly spoken]{volume="soft"} [quickly spoken]{rate="fast"} [higher
pitch]{pitch="high"}.

[More expressive]{pitch="high" rate="fast" volume="loud"}.

:::{pitch="x-high" rate="x-fast" volume="x-loud"} This whole block is loud, fast, and
high-pitched. :::

# Say-as and Substitution

Today on [31.12.2024]{as="date" format="dd.mm.yyyy"}, my telephone number is
[+1-555-0123]{as="telephone"}.

[NASA]{as="characters"} stands for National Aeronautics and Space Administration. The
[1st]{as="ordinal"} place winner gets a prize.

I'd like to drink some [H2O]{sub="water"}. [AWS]{sub="Amazon Web Services"} provides
cloud computing.

# Audio

[doorbell]{src="https://example.com/sounds/bell.mp3"} [music]{clip="5s-30s"
src="song.mp3"} [jingle]{repeat="3" src="ad.mp3"}

# Combining and Nesting Annotations

[[Bonjour]{lang="fr-FR"}]{rate="slow" volume="loud"}
[[important]{as="characters"}]{volume="x-loud"}.

Der Film [Guardians of the *Galaxy*]{lang="en-GB"} ist [sehr]{volume="loud"}
**wichtig**.
