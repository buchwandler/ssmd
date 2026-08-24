# SSMD Example File

# Compiled from SPECIFICATION.md - contains all feature examples

## Text - Basic

text & more

## Emphasis

_moderate emphasis_ **strong emphasis** ~~reduced emphasis~~
[moderate]{emphasis="moderate"} [strong]{emphasis="strong"}
[reduced]{emphasis="reduced"} [no emphasis]{emphasis="none"}

## Break

Hello ...n world Hello ...w world Hello ...c world Hello ...s world Hello ...p world
Hello ...5s world Hello ...100ms world Hello ... world

## Language - Inline

Ich sah [Guardians of the Galaxy]{lang="en"} im Kino. Ich sah [Guardians of the
Galaxy]{lang="en-GB"} im Kino. I saw ["Die Häschenschule"]{lang="de"} in the cinema.
[Bonjour]{lang="fr"} tout le monde!

## Language - Directive (Block Syntax)

<div lang="en-us">
Welcome to the show! I'm Sarah.
</div>

<div lang="en-gb">
Thanks Sarah! Great to be here.
</div>

## Voice - Inline

[Hello]{voice="Joanna"} [Hello]{voice="en-US-Wavenet-A"} [Bonjour]{voice-lang="fr-FR"
gender="female"} [Text]{voice-lang="en-GB" gender="male" variant="1"}

## Voice - Directive (Block Syntax)

<div voice="sarah">
Welcome to the show! I'm Sarah.
</div>

<div voice="michael">
Thanks Sarah! Great to be here.
</div>

<div voice="narrator" voice-lang="en-GB">
This story takes place in London.
</div>

<div voice-lang="fr-FR" gender="female">
Bonjour tout le monde!
</div>

<div gender="female">
Hello World.
</div>

## Mark

I always wanted a @animal cat as a pet. Click @here to continue.

## Paragraph

First prepare the ingredients. Don't forget to wash them first.

Lastly mix them all together.

Don't forget to do the dishes after!

## Heading

# Main Heading

## Subheading

### Sub-subheading

## Phoneme

[tomato]{ph="təˈmeɪtoʊ"} [tomato]{ipa="təˈmeɪtoʊ"} The German word ["dich"]{sampa="dIC"}
does not sound like dick.

## Prosody - Named values and shorthand

[silent]{volume="silent"} [silent]{volume="x-soft"} [silent]{volume="soft"}
[medium]{volume="medium"} medium [loud]{volume="loud"} [x-loud]{volume="x-loud"}

[x-slow]{rate="x-slow"} [slow]{rate="slow"} [medium]{rate="medium"} [fast]{rate="fast"}
[x-fast]{rate="x-fast"}

[x-low]{pitch="x-low"} [low]{pitch="low"} [medium]{pitch="medium"} [high]{pitch="high"}
[x-high]{pitch="x-high"}

[extra loud, fast, and high]{vrp="555"} ++extra loud++ >>extra fast>> ^^extra high^^
_reduced emphasis_ remains reduced emphasis in the Python dialect.

## Prosody - Explicit Notation

[extra loud, fast, and high]{v="5" r="5" p="5"} [extra loud, fast, and high]{v="5" r="5"
p="5"} [loud and slow]{v="4" r="2"}

## Prosody - Relative Values

[louder]{v="+10dB"} [quieter]{v="-3dB"} [faster]{r="+20%"} [slower]{r="-10%"}
[higher]{p="+15%"} [lower]{p="-4%"}

## Prosody - Directive

<div volume="x-loud" rate="x-fast" pitch="x-high">
extra loud, fast, and high
</div>

<div volume="5" rate="5" pitch="5">
extra loud, fast, and high
</div>

<div volume="4" rate="2">
loud and slow
</div>

## Say-as

Today on [31.12.2024]{as="date" format="dd.mm.yyyy"} my telephone number is
[+1-555-0123]{as="telephone"}. You can't say [damn]{as="expletive"} on television.
[NASA]{as="character"} stands for National Aeronautics and Space Administration. The
[1st]{as="ordinal"} place winner gets a prize. Call me at [123]{as="digits"} for more
info.

## Say-as - Detail Attribute

[123]{as="cardinal" detail="2"} [12/31/2024]{as="date" format="mdy" detail="1"}

## Substitution

I'd like to drink some [H2O]{sub="water"} now. [AWS]{sub="Amazon Web Services"} provides
cloud computing. [NATO]{sub="North Atlantic Treaty Organization"} was founded in 1949.

## Audio - Basic

[doorbell]{src="https://example.com/sounds/bell.mp3"} []{src="beep.mp3"} [cat
purring]{src="cat.ogg" alt="Sound file not loaded"}

## Audio - Advanced Attributes

[music]{src="song.mp3" clip="5s-30s"} [announcement]{src="speech.mp3" speed="150%"}
[jingle]{src="ad.mp3" repeat="3"} [alarm]{src="alert.mp3" level="+6dB"} [bg
music]{src="music.mp3" clip="0s-10s" speed="120%" level="-3dB" alt="Fallback text"}

## Extensions - Amazon Polly

[whispered text]{ext="whisper"} [announcement with dynamic range compression]{ext="drc"}

## Combining Annotations

[Bonjour]{lang="fr" volume="x-loud" rate="slow"} [important]{volume="x-loud"
as="character"} [Hello]{voice="Joanna" volume="loud" rate="medium"}

## Nesting and Duplicate Annotations

Der Film [Guardians of the *Galaxy*]{lang="en-GB"} ist ganz [okay]{lang="en-US"}. [very
*important*]{volume="x-loud" emphasis="strong"}
