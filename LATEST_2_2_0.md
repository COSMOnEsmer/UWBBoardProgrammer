# UWB Board Programmer 2.2.0 — Auto Survey

Open **START_HERE_2_2_0.cmd** after a complete clone/pull. It creates the explicitly
versioned **UWB Board Programmer 2.2.0** Desktop shortcut. Earlier releases are preserved.

The full six-page application now includes **Survey & calibration → Auto Survey /
Calibration**. Measure TWR to the Tag at four known, non-coplanar points; accumulate
ranges across sequentially powered anchors; review XYZ/quality; save a new profile;
and restore the normal battery Tag image. Six inter-anchor links are optional diagnostics.

- [คู่มือภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v4.th.md)
- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v4.en.md)
- [Validation and remaining physical acceptance](deployment/VALIDATION.v4.md)

One stationary Tag cannot define unknown anchor XYZ/axes. This workflow requires
physically measured reference positions. Completed physical four-reference calibration
and held-out 3D TDoA accuracy remain to be demonstrated; accepted fixes are never fabricated.

Anchor images: **1.4.1-pilot**. USB calibration Tag: **1.4.2-pilot** (awake USB use).
Normal CR2032 Tag: existing **1.3.4-pilot**. Flash one board at a time is supported.
