# Part 3: Tracking daily attendance for 1,000 people across 100 locations — without smartphones

**Constraint, restated:** no smartphones and no apps exist. Everything else does: landlines,
feature phones (calls + SMS, no apps), basic computers/kiosks, the regular internet, and LLMs
(text and voice). ~10 people per location on average, 100 locations, every working day.

## The core idea: turn attendance into a voice conversation, not a data-entry task

Without an app, there's no "tap to check in." But there doesn't need to be — an LLM-driven voice
agent (exactly the kind of system built in Parts 1–2 of this assignment, e.g. Hunar) can *call
out to* or *receive calls from* any phone, smart or not. So the design centers on **voice as the
input device**, with a lightweight computer/kiosk per location as the supervisor's fallback and
oversight layer.

## System design

**1. Employee-initiated check-in (primary path): missed call / IVR line**

- Every employee is issued one memorized short code or dials one standard number from any
  phone at their location (their own feature phone, or a shared landline at the site) at
  shift start and shift end.
- An LLM voice agent answers, asks the employee to state their name and employee ID (or the
  employee keys in an ID via DTMF tones for speed and to avoid mishearing), and confirms back:
  "Checking in Ramesh Kumar, employee 4021, at the Whitefield site, 9:04 AM — is that correct?"
  A yes/no or a keypress confirms it.
- The call itself supplies two of the three things attendance needs "for free": *who* (voice/ID)
  and *when* (call timestamp). *Where* is inferred from the caller's registered site phone
  number/extension — each location has its own number or extension range, so the system knows
  the location without asking. This is the same caller-ID-based trick a Hunar-style system
  already uses for outbound calls, just inverted for inbound.
- This is cheap and fast to scale: 1,000 employees × 2 calls/day × ~30 seconds each is a trivial
  load for a voice-agent platform designed to place/receive thousands of calls a day.

**2. Supervisor-initiated fallback: outbound roll-call calls**

- At each of the 100 locations, one supervisor or site lead has a basic phone. At a fixed time
  each morning, the system places an automated outbound call to the supervisor and walks them
  through a quick roll call: "Reply 1 if all 10 team members are present, or say the names of
  anyone absent." The LLM agent parses the spoken names against the roster (fuzzy-matching
  handles mispronunciation) and logs exceptions.
- This gives 100% coverage even for employees who forget to self-check-in, without needing every
  individual to own a private phone — it only requires the *site* to be reachable, which is a
  far easier bar to clear at 100 fixed locations than at 1,000 individuals.
- It also naturally handles proxy/buddy-punching concerns better than a self-service system
  alone, since a supervisor is vouching for who's physically there.

**3. Site kiosk (a computer, not an "app"): the audit and correction layer**

- Since basic computers exist, each location gets one shared terminal — a plain web page in a
  browser, not an installed app — where the supervisor can see today's roll call, the LLM's
  live-updating attendance log, and can manually correct/annotate entries (e.g. "approved late
  arrival — client visit"). This is where an LLM-generated natural-language summary is genuinely
  useful: instead of a raw table, the supervisor sees a one-paragraph daily digest ("9 of 10
  present; Priya checked in 40 min late via missed call; Arjun not reached, marked absent
  pending confirmation").
- The same kiosk can run text-based reconciliation: if a call fails (bad line, no answer), the
  LLM sends an SMS to the employee's feature phone ("Reply YES if you're at work today") as a
  second-chance channel that needs no data connection or app, just SMS, which works on every
  phone that exists in this scenario.

**4. Central HR dashboard**

- All 100 locations' logs roll up to one central system (built the same way as the dashboards in
  Parts 1–2 of this assignment: a small web backend aggregating call/SMS results). HR sees
  attendance percentage by location and by employee, exceptions flagged automatically (three
  late check-ins this week, a no-show with no supervisor override, etc.), and can re-trigger a
  call to anyone the system couldn't reach.
- The LLM's role here shifts from "conduct the call" to "read 1,000 daily records and write the
  three things HR actually needs to know" — anomaly detection and a plain-English summary,
  rather than a spreadsheet HR has to comb through manually.

## Why this works at this scale

- **Cost and load are both modest.** ~2,000 short calls/day plus ~100 supervisor calls/day is a
  small fraction of what commercial voice-agent platforms already handle for outbound sales/
  screening use cases (as in Parts 1–2). No per-employee smartphone, data plan, or app install is
  required — only a phone able to receive/place a call, which is the one device guaranteed to
  exist for everyone in this hypothetical.
- **Redundant channels reduce failure points.** Self-check-in → supervisor roll call → SMS
  fallback means a single missed call doesn't turn into a missing attendance record; each layer
  catches what the previous one missed.
- **The system degrades gracefully at low-tech sites.** A location with no computer can still
  fully participate via voice and SMS alone — the kiosk is a convenience for the supervisor, not
  a requirement for the core attendance loop to function.

## Privacy, trust, and failure modes worth flagging

- **Voice-based identity isn't foolproof** — proxy check-ins (a colleague calling in for someone
  absent) are the main integrity risk. The supervisor roll call and periodic random callbacks
  ("we're verifying today's attendance — can you confirm you're on-site?") are the mitigations,
  not a cryptographic guarantee. This is a real trade-off of the no-smartphone constraint: there's
  no biometric or GPS check available, so the design leans on redundancy and spot-checks rather
  than a single strong proof.
- **Consent and recording**: as with any voice-AI system, employees should be told upfront that
  check-in calls are recorded/transcribed and why, and HR should retain only what's needed for
  attendance and payroll purposes.
- **Connectivity gaps** (a site with a spotty landline) need a manual paper-to-kiosk fallback as
  a last resort — worth planning for even though it should be rare across 100 fixed locations.

In short: without a phone app, the phone call itself becomes the interface, and an LLM voice
agent absorbs the job a mobile check-in app would otherwise do — asking the right question,
confirming the answer, and turning a conversation into a structured attendance record.
