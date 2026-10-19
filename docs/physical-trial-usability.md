# Laptop trial usability repair

The first laptop trial recognized blink and smile actions, but did not establish a
completed bona fide session. Logs showed five-second action timeouts. Quality
interruptions also consumed attempts without recording their cause, and the next
frame replaced the useful message with a generic stopped status.

The prototype now allows 12 seconds per action. The main action stays visible
throughout the challenge; secondary feedback updates at most once per second.
Safety failures appear immediately and retain their reason until reset. The
attempt badge stops at the configured attempt limit.

Current-frame MediaPipe face boxes supplement the frontal Haar detector when a
turned face is missed. Haar still runs on every frame. Disjoint detections and
multiple landmark faces remain subject to rejection. An old tracked box cannot
replace a current face detection. PAD thresholds and mandatory operator actions
are unchanged. Any unacceptable quality frame still invalidates challenge and
passive history. During an active action, a disputed multiple-face count blocks
acceptance and clears action history immediately. It spends an attempt only if
the extra detection persists for 0.75 seconds. A transient extra box requires a
fresh action after detection recovers. This is not confirmation that another
person was present. Failure logs include detector box coordinates for diagnosis,
without saving camera images.

Regression tests cover fresh detection fallback, stale-box exclusion, multiple
faces, readable feedback and retained failure reasons. These use controlled
inputs and do not measure physical attack accuracy. A new physical trial is
required to determine whether the changes resolve the reported turning failure.

This laptop application is a research prototype. It does not prove rejection
inside an official MOSIP client or perform identity authentication.
