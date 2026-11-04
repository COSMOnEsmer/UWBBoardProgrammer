# Host-only lifecycle fault injection

These minimal headers are test stand-ins, not vendor headers or firmware inputs.
The harness includes the actual candidate `tag_auto_survey.c`, excludes its RTOS
entry point and supplies controlled API replies. Production compilation uses the
real Murata/NXP SDK in a new copy and never includes this directory.

Run `tools/test_radio_recovery_lifecycle_v1.py` on a Windows development machine
with Visual Studio C build tools. It creates all binaries/logs in a new verification
folder. These tests verify error propagation and bounded HPD recovery; they do not
simulate RF, assess ranging accuracy, or validate battery current/lifetime.
