# 2.7.0 workspace redesign

## Brief and visual system

The user rejected the 2.6.0 MDI workspace because stacked window chrome, tiled cards and repeated headings made it difficult to use. The reference is [survey-concept.png](survey-concept.png), generated with the built-in Image Gen tool as a full native desktop UI concept. The brief required the existing six workflows, a full-width anchor table, a workspace/Auto Survey row, collapsed advanced calibration and log, and subtle Open window controls. No marketing content or invented live metrics were requested.

Tokens: cool background #f4f7fa, white surfaces, navy #11283f navigation, ink #172b42, muted #66788c, teal #087f94 accent, border #dce5ee. Segoe UI/Tahoma: 27px page title, 16px section title, 13px controls and 11–12px secondary text. One reusable Panel and native Dock implementation owns headers, collapse, floating and return actions.

## Verification method

This is a native PySide6 application, not a browser surface. Browser/IAB cannot render its actual widgets. QA therefore uses QApplication rendering and widget interaction tests, not a browser reconstruction. tools/verify_design_v15.py captures all six real pages in both languages at 1366×768, 1568×1003 (the generated concept's native dimensions), and 1920×1080. No Flash, BLE connection or cloud publication is started.

## Fidelity ledger

| Point | Concept evidence | Implementation and adjustment |
| --- | --- | --- |
| Hierarchy | Full-width geometry table above forms | Table spans the page; form/Auto Survey regions sit below; both advanced sections start collapsed. |
| Container model | Single section heading, no OS mini-window bars | Replaced MDI windows with custom dock headers; removed inner duplicate headings on metrics, Auto Survey and log. |
| Palette/type | Navy rail, white surfaces, teal actions | Shared tokens/styles apply to all six pages. Disabled primary buttons were corrected to look disabled. |
| Spacing/density | Readable table and compact controls | Enforced content minimum heights and whole-page scrolling so table rows and buttons remain reachable. |
| Resize/floating | Divider handles and Open window | Native docking separators resize regions; the same widget objects float and return with Attach or close. |
| Localized copy | Existing engineering workflows | All six workflows remain. Auto Survey steps explicitly require four measured reference points, preserving actual capabilities. |
| Live screen | Coordinated companion screen | Same panel system, a compact XYZ strip, map given more width than clock diagnostics, log collapsed. |

Intentional differences from the image: keep the existing U-chip logo and numbered navigation; preserve existing editable table cells and all 12 geometry columns rather than introduce spinboxes or remove RX/AoA fields; preserve the existing profile bounds JSON field and export action; use flat teal instead of the concept's gradient; retain small Collapse controls as well as Open window. The concept's oversimplified Auto Survey wording is replaced with accurate instructions. Hardware status remains offline in screenshots; there are no fabricated live positions. These are functional constraints, not missing controls.

The implementation is inspected against the concept for layout, typography, colour, copy, spacing and panel anatomy using view_image. Existing RF acquisition, solver, path and publication logic is retained. UI interaction checks cover native floating/Attach/close, resizing, advanced expansion, and field visibility at laptop/desktop dimensions. Layout arrangement is currently session-local.
