# Examples

This page provides practical examples of using SSMD in real-world scenarios.

## Basic TTS Integration

### pyttsx3 (Offline TTS)

```python
import pyttsx3
from ssmd import Document

# Initialize TTS engine
engine = pyttsx3.init()

# Create content with SSMD
text = """
# Welcome Message
*Hello* and welcome!
Please ...500ms listen carefully.
This is [very fast]{rate="x-fast"}.
"""

# Create document with pyttsx3 capabilities
doc = Document(text, capabilities='pyttsx3')

# Convert to SSML
ssml = doc.to_ssml()

# Speak (pyttsx3 handles SSML natively)
engine.say(ssml)
engine.runAndWait()
```

### Google Text-to-Speech

```python
from google.cloud import texttospeech
from ssmd import Document

# Initialize Google TTS client
client = texttospeech.TextToSpeechClient()

# Create content
text = """
*Welcome* to our service.
[Bonjour]{lang="fr"} to our French users!
Please wait ...1s for the next message.
"""

# Create document with Google capabilities
doc = Document(text, capabilities='google')

# Convert to SSML
ssml = doc.to_ssml()

# Prepare TTS request
synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Neural2-J"
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Generate speech
response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

# Save to file
with open("output.mp3", "wb") as f:
    f.write(response.audio_content)
```

#### Google TTS with Speaking Styles

Google Cloud TTS supports speaking styles for Neural2 and Studio voices:

```python
from google.cloud import texttospeech
from ssmd import Document

# Configure Google TTS styles as extensions
doc = Document(config={
    'extensions': {
        'cheerful': lambda text: f'<google:style name="cheerful">{text}</google:style>',
        'calm': lambda text: f'<google:style name="calm">{text}</google:style>',
        'empathetic': lambda text: f'<google:style name="empathetic">{text}</google:style>',
        'apologetic': lambda text: f'<google:style name="apologetic">{text}</google:style>',
    }
})

# Build content with speaking styles
doc.add_sentence("[Welcome to our customer service!]{ext=\"cheerful\"}")
doc.add_sentence("[We understand this must be frustrating.]{ext=\"empathetic\"}")
doc.add_sentence("[We sincerely apologize for the inconvenience.]{ext=\"apologetic\"}")
doc.add_sentence("[Please take a moment to breathe.]{ext=\"calm\"}")

# Generate SSML
ssml = doc.to_ssml()

# Initialize Google TTS client
client = texttospeech.TextToSpeechClient()

# Use a voice that supports styles (Neural2 or Studio)
synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Neural2-F"  # Neural2 voices support styles
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

with open("styled_output.mp3", "wb") as f:
    f.write(response.audio_content)
```

:::{note} Speaking styles are only supported by specific Google Cloud TTS voices
(Neural2 and Studio voices). See the complete example in
`examples/google_tts_styles.py`. :::

### Amazon Polly

```python
import boto3
from ssmd import Document

# Initialize Polly client
polly = boto3.client('polly')

# Create content with Amazon extensions
text = """
*Welcome* to our podcast.
Now for the [secret message]{ext="whisper"}.
Back to normal voice.
"""

# Create document with Polly capabilities
doc = Document(text, capabilities='polly')

# Convert to SSML
ssml = doc.to_ssml()

# Generate speech
response = polly.synthesize_speech(
    Text=ssml,
    TextType='ssml',
    OutputFormat='mp3',
    VoiceId='Joanna'
)

# Save audio
with open('output.mp3', 'wb') as f:
    f.write(response['AudioStream'].read())
```

## Streaming TTS

### Sentence-by-Sentence Processing

```python
from ssmd import Document
import time

# Mock TTS engine for demonstration
class TTSEngine:
    def speak(self, ssml):
        print(f"Speaking: {ssml}")
        time.sleep(0.5)  # Simulate speech duration

engine = TTSEngine()

# Long document
document_text = """
# Chapter 1: The Beginning

It was a dark and stormy night.
The rain fell in torrents.
Lightning flashed across the sky.

# Chapter 2: The Discovery

Suddenly, a sound echoed through the halls.
What could it be?
"""

# Create document with automatic sentence splitting
doc = Document(document_text, auto_sentence_tags=True)

sentence_count = len(list(doc.sentences()))
print(f"Total sentences: {sentence_count}")

# Stream sentences
for i, sentence_doc in enumerate(doc.sentences(as_documents=True), 1):
    print(f"\n[{i}/{sentence_count}]")
    engine.speak(sentence_doc.to_ssml())

print("\nPlayback complete!")
```

### Async TTS Streaming

```python
import asyncio
from ssmd import Document

class AsyncTTSEngine:
    async def speak(self, ssml):
        print(f"Speaking: {ssml[:50]}...")
        await asyncio.sleep(0.5)
        print("Done")

async def stream_document(doc):
    engine = AsyncTTSEngine()
    sentence_count = len(list(doc.sentences()))

    for i, sentence_doc in enumerate(doc.sentences(as_documents=True), 1):
        print(f"\n[Sentence {i}/{sentence_count}]")
        await engine.speak(sentence_doc.to_ssml())

async def main():
    text = """
    Welcome to async TTS.
    Each sentence is processed independently.
    This allows for smooth streaming.
    """

    doc = Document(text, auto_sentence_tags=True)
    await stream_document(doc)

# Run
asyncio.run(main())
```

## Interactive Story Reader

```python
from ssmd import Document
import pyttsx3

class StoryReader:
    def __init__(self, tts_engine='pyttsx3'):
        self.capabilities = tts_engine
        self.engine = pyttsx3.init()
        self.current_doc = None
        self.current_index = 0

    def load_story(self, ssmd_text):
        """Load a story from SSMD text."""
        self.current_doc = Document(
            ssmd_text,
            capabilities=self.capabilities,
            auto_sentence_tags=True
        )
        self.current_index = 0

    def play(self):
        """Play from current position."""
        if not self.current_doc:
            print("No story loaded")
            return

        sentences = list(self.current_doc.sentences(as_documents=True))

        while self.current_index < len(sentences):
            sentence_doc = sentences[self.current_index]
            print(f"\n[{self.current_index + 1}/{len(sentences)}]")

            self.engine.say(sentence_doc.to_ssml())
            self.engine.runAndWait()

            self.current_index += 1

            # Interactive control
            cmd = input("(n)ext, (p)rev, (q)uit: ").lower()
            if cmd == 'q':
                break
            elif cmd == 'p' and self.current_index > 0:
                self.current_index -= 2  # Go back two, play one forward

    def get_progress(self):
        """Get reading progress."""
        if not self.current_doc:
            return 0
        total_sentences = len(list(self.current_doc.sentences()))
        return (self.current_index / total_sentences) * 100 if total_sentences > 0 else 0

# Usage
story = """
# The Adventure Begins

[Once upon a time]{volume="2" rate="2"}, in a land far away.
There lived a brave *knight* named Sir Galahad.
He faced many challenges ...1s but never gave up.

# The Quest

One day, the king summoned him.
[Go forth]{volume="x-loud"} said the king, [and save our kingdom]{volume="x-loud"}!
"""

reader = StoryReader()
reader.load_story(story)
reader.play()
```

## Content Management System

### SSMD CMS with Database

```python
from ssmd import Document, to_ssml
import sqlite3
from datetime import datetime

class SSMDContentManager:
    def __init__(self, db_path='content.db'):
        self.db = sqlite3.connect(db_path)
        self._setup_db()

    def _setup_db(self):
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY,
                title TEXT,
                ssmd_text TEXT,
                ssml_cache TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        self.db.commit()

    def create(self, title, ssmd_text):
        """Create new content."""
        ssml = to_ssml(ssmd_text)
        now = datetime.now()

        self.db.execute('''
            INSERT INTO content (title, ssmd_text, ssml_cache, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, ssmd_text, ssml, now, now))

        self.db.commit()

    def update(self, content_id, ssmd_text):
        """Update existing content."""
        ssml = to_ssml(ssmd_text)
        now = datetime.now()

        self.db.execute('''
            UPDATE content
            SET ssmd_text = ?, ssml_cache = ?, updated_at = ?
            WHERE id = ?
        ''', (ssmd_text, ssml, now, content_id))

        self.db.commit()

    def get_ssml(self, content_id):
        """Get cached SSML for content."""
        cursor = self.db.execute(
            'SELECT ssml_cache FROM content WHERE id = ?',
            (content_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_ssmd(self, content_id):
        """Get SSMD source."""
        cursor = self.db.execute(
            'SELECT ssmd_text FROM content WHERE id = ?',
            (content_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

# Usage
cms = SSMDContentManager()

# Create content
cms.create("Welcome Message", """
# Welcome to Our Service
*Thank you* for joining us today!
""")

# Get SSML for TTS
ssml = cms.get_ssml(1)
print(ssml)
```

## Multi-Language Support

### Language-Aware TTS

```python
from ssmd import Document, to_ssml

class MultilingualTTS:
    def __init__(self):
        self.capabilities = 'google'

    def create_multilingual_content(self, messages):
        """Create content with multiple languages."""
        parts = []

        for lang, text in messages:
            if lang == 'en':
                parts.append(text)
             else:
                 parts.append(f"[{text}]{{lang=\"{lang}\"}}")


        return " ".join(parts)

    def speak_multilingual(self, messages):
        ssmd_text = self.create_multilingual_content(messages)
        ssml = to_ssml(ssmd_text, capabilities=self.capabilities)
        return ssml

# Usage
tts = MultilingualTTS()

messages = [
    ('en', '*Welcome* to our global service.'),
    ('fr', 'Bienvenue à notre service mondial.'),
    ('de', 'Willkommen zu unserem globalen Service.'),
    ('es', 'Bienvenido a nuestro servicio global.'),
]

ssml = tts.speak_multilingual(messages)
print(ssml)
```

## Podcast Generator

```python
from ssmd import Document
from pathlib import Path

class PodcastGenerator:
    def __init__(self, output_dir='podcasts'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_episode(self, episode_number, script):
        """Generate podcast episode."""
        # Add production elements
        enhanced_script = f"""
        # Episode {episode_number}

         [Podcast intro music]{src="@intro_music.mp3"}


        ...1s

        {script}

        ...2s

         [Outro music]{src="@outro_music.mp3"}

        """

        # Create document with Polly capabilities
        doc = Document(
            enhanced_script,
            capabilities='polly',
            auto_sentence_tags=True,
            pretty_print=True
        )

        # Convert to SSML
        ssml = doc.to_ssml()

        # Save SSML
        output_file = self.output_dir / f"episode_{episode_number}.ssml"
        output_file.write_text(ssml)

        return output_file

# Usage
podcast = PodcastGenerator()

script = """
*Welcome* to Tech Talks!
Today we're discussing artificial intelligence.

Our guest is Dr. Smith, an expert in machine learning.
[Welcome to the show]{volume="4"}, Doctor Smith!

...500ms

Thank you for having me.
"""

ssml_file = podcast.generate_episode(42, script)
print(f"Generated: {ssml_file}")
```

## Testing and Validation

### SSMD Linter

```python
from ssmd import to_ssml

class SSMDLinter:
    def lint(self, ssmd_text):
        """Validate SSMD and provide feedback."""
        issues = []

        # Try to convert
        try:
            ssml = to_ssml(ssmd_text)
        except Exception as e:
            issues.append(f"Conversion error: {e}")
            return issues

        # Check for common issues
        if '*' in ssmd_text and '**' not in ssmd_text:
            if ssmd_text.count('*') % 2 != 0:
                issues.append("Unmatched asterisks for emphasis")

        # Check for very long pauses
        if '...10s' in ssmd_text or '...10000ms' in ssmd_text:
            issues.append("Warning: Very long pause detected")

        # Success
        if not issues:
            issues.append("✓ No issues found")

        return issues

# Usage
linter = SSMDLinter()

text = """
*Hello world
This has an unclosed emphasis tag.
"""

issues = linter.lint(text)
for issue in issues:
    print(issue)
```

## Complete Application Example

### Voice Assistant with SSMD

```python
from ssmd import to_ssml
import random

class VoiceAssistant:
    def __init__(self, name="Assistant", tts_engine='google'):
        self.name = name
        self.capabilities = tts_engine

    def greet(self, user_name=None):
        greetings = [
            "*Hello*!",
            "Good day!",
            "*Welcome* back!",
        ]

        greeting = random.choice(greetings)

        if user_name:
            message = f"{greeting} {user_name}."
        else:
            message = greeting

        return to_ssml(message, capabilities=self.capabilities)

    def error(self, message):
        return to_ssml(f"--Sorry-- ...300ms {message}", capabilities=self.capabilities)

    def success(self, message):
        return to_ssml(f"*Great*! {message}", capabilities=self.capabilities)

    def thinking(self):
        return to_ssml("...500ms Let me think ...500ms", capabilities=self.capabilities)

    def announce(self, title, message):
        ssmd = f"""
        # {title}

        ...300ms

        {message}
        """
        return to_ssml(ssmd, capabilities=self.capabilities)

# Usage
assistant = VoiceAssistant(name="Jarvis")

print(assistant.greet("John"))
print(assistant.thinking())
print(assistant.success("Task completed successfully"))
print(assistant.error("I couldn't find that file"))
print(assistant.announce("Weather Update", "It's sunny with a high of 72 degrees"))
```

## Parser API Examples

The Parser API extracts structured data from SSMD instead of generating SSML. This is
useful for building custom TTS pipelines.

### Basic Segment Extraction

```python
from ssmd import parse_segments

text = "Hello *world*! This is ...500ms great."
segments = parse_segments(text)

for seg in segments:
    print(f"Text: {seg.text!r}")
    if seg.emphasis:
        print("  - Has emphasis")
    for brk in seg.breaks_after:
        print(f"  - Break: {brk.time}")
```

### Multi-Voice Dialogue Processing

```python
from ssmd import parse_sentences

script = """
<div voice="sarah">
Welcome to the show!
</div>

<div voice="michael">
Thanks Sarah! Great to be here.
</div>

<div voice="sarah">
Let's get started!
</div>
"""

for sentence in parse_sentences(script):
    voice_name = sentence.voice.name if sentence.voice else "default"
    text = "".join(seg.text for seg in sentence.segments)
    print(f"[{voice_name}] {text}")

compact_script = '<div voice="sarah">Welcome.</div>'
assert parse_sentences(compact_script)[0].voice.name == "sarah"
```

Compact voice blocks are also supported and have the same parsing and reference behavior.

### Custom TTS Pipeline

```python
from ssmd import parse_sentences

class CustomTTS:
    def process_script(self, script):
        """Process SSMD script with custom handling."""
        sentences = parse_sentences(script)

        for sentence in sentences:
            # Configure voice
            voice = sentence.voice.name if sentence.voice else "default"

            # Build text with transformations
            full_text = ""
            for seg in sentence.segments:
                # Handle say-as
                if seg.say_as:
                    if seg.say_as.interpret_as == "telephone":
                        text = self.format_phone(seg.text)
                    elif seg.say_as.interpret_as == "date":
                        text = self.format_date(seg.text)
                    else:
                        text = seg.text
                # Handle substitution
                elif seg.substitution:
                    text = seg.substitution
                # Handle phoneme
                elif seg.phoneme:
                    text = seg.text  # Use phoneme data
                else:
                    text = seg.text

                full_text += text

            # Speak with custom TTS
            self.speak(full_text, voice=voice)

    def format_phone(self, number):
        """Custom phone number formatting."""
        # Remove non-digits and format
        digits = ''.join(c for c in number if c.isdigit())
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

    def format_date(self, date_str):
        """Custom date formatting."""
        return date_str  # Add custom date parsing

    def speak(self, text, voice="default"):
        """Mock TTS speak method."""
        print(f"[{voice}] {text}")

 # Usage
 tts = CustomTTS()
 tts.process_script("""
 <div voice="sarah">
 Call [+1-555-0123]{as="telephone"} today!
 </div>
 """)
```

### Text Transformation Example

```python
from ssmd import parse_segments

 text = """
 Call [+1-555-0123]{as="telephone"} for info.
 [H2O]{sub="water"} is important.
 Say [tomato]{ipa="təˈmeɪtoʊ"} correctly.
 """

segments = parse_segments(text)

for seg in segments:
    if seg.say_as:
        print(f"Say-as: {seg.text!r} as {seg.say_as.interpret_as}")
    elif seg.substitution:
        print(f"Substitute: '{seg.text}' → '{seg.substitution}'")
    elif seg.phoneme:
        print(f"Phoneme: '{seg.text}' → /{seg.phoneme.ph}/")
```

For a complete parser demonstration, see `examples/parser_demo.py`.

## See Also

- Check the `examples/` directory in the repository for more runnable examples:

  - `examples/parser_demo.py` - Complete parser API demonstration
  - `examples/story_reader_demo.py` - Interactive story reader
  - `examples/tts_with_capabilities.py` - TTS engine capability filtering
  - `examples/tts_container_demo.py` - Container-based TTS demo
  - `examples/google_tts_styles.py` - Google Cloud TTS speaking styles

- Visit {doc}`api` for complete API documentation

- See {doc}`parser` for the Parser API guide

- See {doc}`capabilities` for TTS engine integration details
