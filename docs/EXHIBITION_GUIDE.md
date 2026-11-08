# Exhibition guide — running the NEX demo

A 4–6 minute script that shows everything, in the order that builds the
biggest impression.

---

## Before the demo (5 minutes)

1. **Wake the backend.** Free Render instances sleep. Open the app and say
   *"Hey NEX, hello"* once so the server is awake.
2. **Phone setup**
   - Microphone permission: **granted**
   - Camera permission: **granted**
   - Do **not** leave the screen on with the app in the background — Android
     stops the microphone when the app is not in the foreground.
   - Turn on "Do not disturb"? *No* — the TTS should be audible.
3. **Server address** — long-press the eyes once, confirm the status dot is
   green, close the panel.
4. **Volume** — media volume up, ringer volume up.

---

## The demo

### 1. The face (10 seconds)

Launch NEX. Pure black screen, two cyan eyes. It blinks, looks around, and
greets you:

> *"Hi! I am NEX, your AI robot pet. Say 'Hey NEX' and talk to me!"*

Do not touch the phone — NEX is hands-free.

### 2. A real conversation (30 seconds)

> *"Hey NEX, how are you today?"*
> *"NEX, tell me something about robots."*
> *"NEX, apna favourite animal batao."*

Point out that it is **listening, thinking and speaking** — the eyes show each
state, and it answers in the language you used.

### 3. The creators (15 seconds)

> *"NEX, tumhe kisne banaya?"*

It answers with the exact sentence:

> *"Mujhe Arnav, Divya aur Aryan ne banaya hai! Main hoon NEX — tumhara smart aur masti karne wala AI robot pet!"*

### 4. Animal voices (45 seconds — the crowd favourite)

> *"NEX, dog ki awaaz nikalo!"*
> *"NEX, lion ki awaaz sunao!"*
> *"NEX, elephant ki awaaz!"*
> *"NEX, frog bhi bol sakta hai kya?"*
> *"NEX, ek bird ki awaaz!"*

Twenty voices in total — dog, cat, cow, lion, tiger, monkey, elephant, duck,
chicken, horse, sheep, goat, wolf, frog, bird, pig, donkey, rooster, owl, bee.

### 5. Dance + emotions (30 seconds)

> *"NEX, dance!"* → the eyes really dance.
> *"NEX, ek joke sunao!"* → laugh expression.
> *"NEX, mujhe apne school ke baare mein batao."* → grounded school answer
  from the school's own website.

### 6. It sees (30 seconds)

Hold an object (a book, a bottle, your hand) in front of the front camera and say:

> *"NEX, ye kya hai?"*

It describes the object through Gemini Vision. Then point the camera at
someone's face — NEX reacts to faces on its own via on-device ML Kit detection.

### 7. Multilingual finale (30 seconds)

Say the same request in different languages and let NEX switch:

> *"Hey NEX, what's the weather like today?"* (English)
> *"NEX, aaj mausam kaisa hai?"* (Hinglish)
> *"NEX, आज मौसम कैसा है?"* (Hindi)

---

## Crowd questions — prepared answers

| Question | Say to NEX |
| --- | --- |
| "Who made it?" | *"NEX, tumhe kisne banaya?"* |
| "Does it work offline?" | *"NEX, bina internet ke kya kar sakte ho?"* |
| "What technology is this?" | *"NEX, tum kis technology se bane ho?"* |
| "Can it see me?" | Point the camera: *"NEX, ye kya hai?"* |
| "Is this real AI or pre-recorded?" | *"NEX, tumhara real AI ho ya recording? "* — it calls Gemini for every answer |
| "What's your name?" | *"NEX, tumhara naam kya hai?"* |

---

## Troubleshooting on the day

| Symptom | Fix |
| --- | --- |
| Eyes look **sad** at launch | Backend unreachable → long-press → set the server URL → **Test & save** |
| Eyes stay **angry** | Microphone permission denied → long-press → **Microphone** |
| NEX ignores you | You did not say "Hey NEX" (wake word is on) — say it clearly, or turn the wake word off in the setup panel |
| NEX answers but you cannot hear it | Media volume is muted |
| NEX thinks for a long time | Free-tier cold start — wait ~45 s, then it is fast |
| NEX talks to itself | Tap the eyes once to pause listening, then tap again |

---

## Quick reference card

```
WAKE WORD      Hey NEX
SETUP PANEL    long-press the eyes (1 s)
PAUSE MIC      tap the eyes
ANIMALS        20 voices
LANGUAGES      Hindi · Hinglish · English · +40 more
CREATORS       Arnav, Divya and Aryan
```
