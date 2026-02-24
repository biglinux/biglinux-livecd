# PLANNING.md — Project Improvement Roadmap

## Files Analyzed

**Total files read:** 34  
**Total lines analyzed:** 6,561  
**Large files (>500 lines) confirmed read in full:**
- `biglinux-livecd/usr/share/biglinux/livecd/services.py` — 718 lines (read in entirety: lines 1–718)
- `biglinux-livecd/usr/share/biglinux/calamares/src/services/install_service.py` — 625 lines (read in entirety: lines 1–625)

**All 34 files read completely:**
- Livecd app: `main.py`, `application.py`, `config.py`, `logging_config.py`, `services.py`, `translations.py`
- Livecd UI: `app_window.py`, `base_view.py`, `desktop_view.py`, `keyboard_view.py`, `language_view.py`, `theme_view.py`, `init.py`
- Calamares app: `main.py`, `src/app.py`, `src/window.py`
- Calamares pages: `__init__.py`, `main_page.py`, `maintenance_page.py`, `minimal_page.py`, `tips_page.py`
- Calamares services: `__init__.py`, `system_service.py`, `package_service.py`, `install_service.py`
- Calamares utils: `__init__.py`, `constants.py`, `helpers.py`, `i18n.py`, `shell.py`, `widgets.py`
- Calamares modules: `btrfs/main.py`, `btrfs-fix/main.py`, `grubcfg-fix/main.py`
- CSS: `style.css` (121 lines, read in full)

---

## Current State Summary

**Grade: C+ (Functional but needs significant accessibility and architecture work)**

### What Works
- The livecd first-run wizard is functional with a clear multi-step flow (Language → Keyboard → Desktop → Theme).
- Lazy loading of views is properly implemented, improving startup performance.
- Test mode prevents system modifications during development.
- Dynamic translation (retranslation on language change) works across views.
- The calamares configuration tool has clean service separation and proper singleton management.
- Both applications use GTK4/Adwaita correctly for basic layouts.

### What Doesn't Work / Needs Attention
- **Accessibility is now functional for Orca** ✅ — all interactive widgets have accessible names/labels; switches have LABELLED_BY relations; settings cards are keyboard-focusable; logo images have alt text; search entry is labeled.
- **No test suite exists** — zero automated tests for 6,500+ lines of code.
- **Code duplication** — JamesDSP enable/disable logic is duplicated in `services.py` (`apply_jamesdsp_settings()` and `finalize_setup()`); XivaStudio detection is duplicated across livecd and calamares.
- **High cyclomatic complexity** — `_modify_settings_file()` has CC=24 (grade D), making it fragile and hard to maintain.
- **Hardcoded colors in CSS** — many colors bypass Adwaita theming, breaking with system theme changes.
- **Calamares app uses AdwToastOverlay** — per project guidelines, this should use alternative feedback mechanisms.
- **`ui/init.py` should be `ui/__init__.py`** — wrong filename prevents proper Python package recognition.

---

## Critical (fix immediately)

### Accessibility — Orca Screen Reader

- [x] ✅ **No accessible names on step buttons**: `app_window.py:245-252` — Header step buttons have only SVG images, no label or `accessible-name`. Orca announces nothing ("button"). → Add `button.update_property(Gtk.AccessibleProperty.LABEL, step_name)` for each step button. **IMPLEMENTADO**: Adicionado `_STEP_LABELS` dict com lambdas traduzíveis; `update_property(LABEL)` chamado na criação e no `_retranslate_ui()`. Botões agora `set_focusable(True)`.

- [x] ✅ **FlowBox items lack accessible names**: `base_view.py:117-126` — `FlowBoxChild` items have no accessible description. Orca cannot announce what item is selected. → Set `flow_child.update_property(Gtk.AccessibleProperty.LABEL, name)` on each child. **IMPLEMENTADO**: `flow_child.update_property([Gtk.AccessibleProperty.LABEL], [item_obj.name])` adicionado em `load_items()`.

- [x] ✅ **Language GridView items inaccessible**: `language_view.py:185-230` — Language items have visual flag + text but no accessible name on the list item root. Orca says "cell" with no context. → Set accessible label to `f"{item.name} ({item.name_orig})"` on the root box. **IMPLEMENTADO**: `root_box.update_property([Gtk.AccessibleProperty.LABEL], [f"{item.name} ({item.name_orig})"])` adicionado em `_on_factory_bind()`.

- [x] ✅ **Keyboard layout buttons lack accessible names**: `keyboard_view.py:128-150` — FlowBoxChild widgets have `layout_data` dict but no accessible label. Orca says "child" without announcing the layout. → Set `flow_child.update_property(Gtk.AccessibleProperty.LABEL, f"Keyboard layout: {name}")`. **IMPLEMENTADO**: Label acessível traduzível `_("Keyboard layout: %s") % name` adicionado. Imagem SVG do teclado ganhou label `_("Keyboard layout preview")`.

- [x] ✅ **Theme cards inaccessible**: `theme_view.py:255-310` — Theme items are image-only (full mode) with no accessible description. A blind user has zero information. → Set accessible label to theme name on each widget. **IMPLEMENTADO**: Modo simplificado recebe `update_property(LABEL, label_text)`. Modo completo resolvido via `base_view.py` (labels nos FlowBoxChild).

- [x] ✅ **Switches lack accessible relationships**: `theme_view.py:161-180, 195-215` — JamesDSP and Contrast switches are standalone `Gtk.Switch` widgets not associated with their labels via `set_accessible_relation()`. Orca announces "switch, off" without context. → Use `switch.update_relation(Gtk.AccessibleRelation.LABELLED_BY, [title_label])`. **IMPLEMENTADO**: `jamesdsp_switch.update_relation([LABELLED_BY], [jamesdsp_title_label])` e `contrast_switch.update_relation([LABELLED_BY], [contrast_title_label])` adicionados.

- [x] ✅ **Search entry has no accessible label**: `language_view.py:72-76` — `Gtk.SearchEntry` has placeholder text but no programmatic accessible name. → Add `self.search_entry.update_property(Gtk.AccessibleProperty.LABEL, _("Search for a language..."))`. **IMPLEMENTADO**: `update_property(LABEL)` adicionado na criação e no `_retranslate_ui()`.

- [x] ✅ **Settings cards not keyboard-focusable**: `theme_view.py:148-217` — Settings card boxes (`Gtk.Box`) are not focusable; only the switch inside is. Tab navigation skips the card entirely. → Make the entire card a button or ensure the switch is properly tab-reachable independent of the card click gesture. **IMPLEMENTADO**: `audio_card.set_focusable(True)` e `contrast_card.set_focusable(True)` adicionados. CSS focus-within/focus-visible adicionados para feedback visual.

### Security

- [ ] **`subprocess.call()` without error handling in calamares modules**: `btrfs/main.py:42-46`, `btrfs-fix/main.py:39` — `subprocess.call()` return values are silently ignored. Failures go undetected. → Check return codes and log errors.

- [ ] **Forum link opens browser as different user via `su`**: `main_page.py:105-118` — Uses `subprocess.Popen(['su', user, '-c', f'xdg-open {uri}'])` with string interpolation in a shell command via `su -c`. This is a command injection vector if `uri` is malicious. → Use `subprocess.Popen(['su', user, '-c', 'xdg-open "$1"', '--', uri])` or better, use `gio open` without `su`.

### Missing Tests

- [ ] **No test suite**: The project has 0 test files. For a system configuration wizard that modifies locale, keyboard, timezone, and desktop themes, this is critical. → Create `tests/` directory with:
  - Unit tests for `services.py` (mock subprocess calls)
  - Unit tests for `config.py` data classes
  - Unit tests for `translations.py` language switching
  - Integration tests for view signal chains
  - Calamares service tests for configuration generation

### Package Structure

- [ ] **`ui/init.py` wrong filename**: `ui/init.py` is an empty file but should be named `ui/__init__.py`. The current name means `from ui import X` works by accident (via `sys.path` manipulation) rather than proper package structure. → Rename to `ui/__init__.py`.

---

## High Priority (code quality)

### Code Duplication

- [ ] **JamesDSP logic duplicated**: `services.py:482-530` (`apply_jamesdsp_settings`) duplicates the same logic in `services.py:480-520` (`finalize_setup`). → Extract shared `_set_jamesdsp_state(enabled: bool)` method called by both.

- [ ] **XivaStudio detection duplicated across apps**: `services.py:696-718` (livecd), `window.py:22-33` (calamares), `main_page.py:22-36` (calamares). Three separate implementations of the same check. → Create shared utility module or consolidate into one location.

- [ ] **`_create_option_card` duplicated**: `maintenance_page.py:51-98` duplicates `widgets.py:create_option_card()`. → Use the shared widget factory from `utils/widgets.py`.

### Complexity

- [ ] **`_modify_settings_file()` CC=24**: `services.py:348-460` — This 112-line method has deeply nested loops and conditionals for INI-like file parsing. → Extract into a proper `DconfSettingsEditor` class, or use `configparser` if the format allows. Consider splitting into `_parse_sections()`, `_apply_modifications()`, `_write_file()`.

- [ ] **`_on_language_selected()` CC=12**: `app_window.py:317-370` — Does too many things: saves config, applies settings, retranslates UI, updates header icon, determines keyboard layout, creates views, and navigates. → Split into `_apply_language_config()`, `_update_language_ui()`, `_navigate_after_language()`.

- [ ] **`ShellExecutor.execute()` CC=19**: `shell.py:43-150` — Complex branching for timeout, shell mode, output capture, process kill. → Consider splitting timeout handling into a decorator or context manager.

### Type Safety

- [ ] **Missing `Optional` annotation**: `app_window.py:26,39` — `system_service: SystemService = None` should be `system_service: Optional[SystemService] = None`. mypy reports this. → Fix type hints.

- [ ] **`completed_steps` missing type annotation**: `app_window.py:71` — `self.completed_steps = set()` needs `self.completed_steps: set[str] = set()`. → Add annotation.

- [ ] **Dynamic base class warning**: `base_view.py:17` — `GObjectMeta(type(GObject.Object), ABCMeta)` triggers mypy `misc` error. This is a known GTK/GObject metaclass pattern; suppress with `# type: ignore[misc]`.

### Linting

- [ ] **65 E402 violations (import not at top)**: All files using `gi.require_version()` followed by imports trigger this. → Add `# noqa: E402` comments or configure ruff to ignore E402 for GTK files.

- [ ] **2 F541 f-string without placeholders**: Ruff reports f-strings with no interpolation. → Remove the `f` prefix.

- [ ] **1 F401 unused import**: Unused import detected. → Remove.

- [ ] **23 files need reformatting**: ruff format reports formatting issues. → Run `ruff format .` to auto-fix.

---

## Medium Priority (UX improvements)

### Cognitive Load & Progressive Disclosure

- [ ] **Theme view cramming**: `theme_view.py:80-85` — Full mode shows 4-8 columns of theme thumbnails plus settings switches at the bottom. For KDE with many themes, this can show 20+ items at once exceeding Miller's 7±2 rule. → Group themes by category (light/dark/colorful) with sub-groups, showing 6-8 per group.

- [ ] **No undo/back from theme selection**: `app_window.py:420-445` — Clicking a theme immediately applies it and closes the app. There is no confirmation. The user cannot preview a theme without committing. **Psychology: Error prevention > error correction (Norman's design principle).** → Add a preview delay or confirmation step: "Apply this theme and finish setup?"

- [ ] **Keyboard view only shows 2 layouts**: `keyboard_view.py:110-117` — Only shows the auto-detected layout and US. Users who want a different layout (e.g., UK, Dvorak) have no option. → Add a "More layouts..." expandable section or search.

- [ ] **No visible feedback during language application**: `app_window.py:317-370` — After clicking a language, system commands run (timedatectl, localectl) with no loading indicator. **Psychology: Users need feedback within 400ms or they assume the action failed (Doherty threshold).** → Show a briefly visible spinner or progress indicator during apply.

- [ ] **Step icons pulse animation on current step**: `style.css:4-18` — Pulsing animation on the current step icon can be distracting for users with vestibular disorders. → Add `@media (prefers-reduced-motion: reduce)` to disable animation, per WCAG 2.3.3.

### Visual Design

- [ ] **Hardcoded colors break theming**: `style.css:37-44` — Colors like `#fff`, `#000`, `#222` are hardcoded instead of using Adwaita CSS variables (`@theme_fg_color`, etc.). This breaks if system theme changes or user uses high-contrast mode. → Replace with `color: @theme_fg_color;` and equivalent variables.

- [ ] **`.title-2` uses `text-shadow`**: `style.css:37-40` — Text shadows reduce readability for low-vision users and are not part of GNOME HIG. → Remove text-shadow or make it optional via a helper CSS class.

- [ ] **Keyboard cards use hardcoded gradients**: `style.css:93-110` — Background gradients bypass Adwaita theming. → Use `@headerbar_bg_color` or card-like styling from Adwaita.

### Feedback Mechanisms

- [ ] **Calamares app uses AdwToastOverlay**: `window.py:80` — Per project requirements, AdwToastOverlay should not be used for critical feedback. → Replace with inline status labels or `Adw.MessageDialog` for error states. Non-critical notifications can use a custom inline bar.

- [ ] **`on_preferences_action` uses Toast**: `app.py:129` — "Preferences not implemented yet" as a Toast is a poor UX choice for an unimplemented feature. → Either implement preferences or remove the action entirely to avoid confusing users.

---

## Low Priority (polish & optimization)

- [ ] **`label.set_ellipsize(True)` incorrect API**: `theme_view.py:307` — `set_ellipsize()` expects a `Pango.EllipsizeMode`, not `True`. This likely does nothing or triggers a warning. → Change to `label.set_ellipsize(Pango.EllipsizeMode.END)`.

- [ ] **Cursor set in try/except**: Multiple files (`keyboard_view.py:137`, `language_view.py:170`, `desktop_view.py:48`, `theme_view.py:264,290`) — All cursor changes wrapped in bare `except Exception: pass`. → Either always set cursor (it won't fail in GTK4) or use a utility function.

- [ ] **Unused variables from callbacks**: `app_window.py:265,486`, `base_view.py:139,158`, `keyboard_view.py:173,188`, `language_view.py:146,202,252`, `theme_view.py:219,331` — Vulture reports 21 unused variables, mostly from GTK signal callback parameters. → Prefix with `_` (e.g., `_keycode`, `_state`, `_y`) to indicate intentionally unused.

- [ ] **`Gtk.Picture.new_for_pixbuf()` deprecated**: `desktop_view.py:59`, `theme_view.py:297` — `new_for_pixbuf()` is deprecated in GTK 4.12+. → Use `Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))`.

- [ ] **`application.py:38` f-string in logger.warning**: → Use `logger.warning("...not found at %s", flags_dir)` for lazy evaluation.

- [ ] **Hover-to-select disrupts keyboard navigation**: `base_view.py:127-128`, `keyboard_view.py:160-161` — Mouse hover selects the item under the cursor, stealing selection from keyboard navigation. If a user navigates with arrows, moving the mouse resets selection. → Only activate hover-select when mouse has moved; track last interaction mode.

---

## Architecture Recommendations

### 1. Separate Livecd and Calamares as Packages

Currently both apps share the same repository but have independent code. They should have clearer boundaries:
- Create `pyproject.toml` or `setup.cfg` for each app
- Share translation files via a common locale directory (already done)
- Consider extracting shared XivaStudio detection into a shared utility

### 2. Introduce State Machine for Wizard Flow

The current step navigation in `app_window.py` uses ad-hoc `completed_steps` set and manual `_ensure_view()` calls. This is fragile:
- Step ordering is implicit in the signal callbacks
- Skip logic (keyboard auto-skip) is buried in `_on_language_selected()`
- Adding/removing steps requires changes in multiple methods

→ Create a `WizardStateMachine` class that defines:
- Step sequence based on detected environment
- Transition rules (when to skip, when to auto-advance)
- State persistence

### 3. Extract Theme Application Logic

Theme application (`_apply_dark_theme`, `_apply_light_theme`) in `services.py:222-330` contains hardcoded theme names, icon names, and desktop-specific logic. This should be data-driven:
- Define theme configurations in a JSON/TOML file
- `services.py` reads the config and applies generically
- Adding new desktop environments means adding config, not code

### 4. ui/__init__.py Fix

Rename `ui/init.py` to `ui/__init__.py` for proper Python package structure. This also enables proper mypy checking.

---

## UX Recommendations

### 1. Confirmation Before Destructive Actions

**Principle: Error Prevention (Don Norman)**  
Currently, selecting a theme immediately applies it AND closes the application. There is no way back. For a first-run wizard where users are exploring options, this is hostile.

**Recommendation:** After theme selection, show a 2-second preview with a "Confirm & Finish" button. Allow users to browse themes without committing.

### 2. Progress Indication

**Principle: Feedback / Doherty Threshold (400ms)**  
Language changes trigger `timedatectl`, `localectl`, and `setxkbmap` — operations that can take 1-3 seconds. No visual feedback is shown.

**Recommendation:** Show a subtle spinner or progress bar during system operations. Use `GLib.idle_add()` to update UI after async operations complete.

### 3. Keyboard Layout Discovery

**Principle: Recognition Over Recall (Nielsen)**  
The keyboard view shows only 2 options. Users who need Dvorak, Colemak, or regional variants (UK, ABNT2 when not auto-detected) have no escape hatch.

**Recommendation:** Add a "Show all layouts" expander or search field below the primary options.

### 4. Forgiving Navigation

**Principle: Forgiveness (Cooper)**  
Steps can be revisited, but only by clicking completed step icons. Users may not discover this affordance.

**Recommendation:** Add explicit "Back" button text or arrow, visible at all times except on the first step.

### 5. First-Run Guidance

**Principle: Recognition Over Recall**  
The wizard assumes users understand what "Desktop Layout" and "Theme" mean. New Linux users may not.

**Recommendation:** Add subtitle text under step titles: "Choose how your desktop panels and menus are arranged" for Desktop Layout.

---

## Orca Screen Reader Compatibility

### Issues Found

| Widget | File:Line | Problem | Fix |
|--------|-----------|---------|-----|
| Step buttons | `app_window.py:245` | No accessible name. Orca: "button" | `button.update_property(Gtk.AccessibleProperty.LABEL, _("Step: Language"))` |
| FlowBox children | `base_view.py:117` | No accessible label. Orca: "child" | `flow_child.update_property(Gtk.AccessibleProperty.LABEL, name)` |
| Language grid items | `language_view.py:185` | Orca: "cell" — no language name | Set accessible label: `f"{item.name} ({item.name_orig})"` |
| Keyboard FlowBox items | `keyboard_view.py:128` | Orca: "child" — no layout name | Set accessible label to layout name |
| Desktop FlowBox items | `desktop_view.py:45` | Image-only cards. Orca: "child" — no desktop name | Set accessible label to layout name |
| Theme FlowBox items (full) | `theme_view.py:280` | Image-only. Orca: "child" | Set accessible label to theme name |
| Theme cards (simplified) | `theme_view.py:255` | Has icon + label but no accessible name on root | Set accessible label: "Dark Theme" / "Light Theme" |
| JamesDSP switch | `theme_view.py:178` | Not labelled-by title. Orca: "switch, off" | `switch.update_relation(Gtk.AccessibleRelation.LABELLED_BY, [title_label])` |
| Contrast switch | `theme_view.py:215` | Same as above | Same fix |
| Search entry | `language_view.py:74` | No accessible programmatic label | `update_property(Gtk.AccessibleProperty.LABEL, ...)` |
| Logo images | `app_window.py:157,168` | Decorative images lack `accessible-role=NONE` | Mark as presentation: `logo.update_property(Gtk.AccessibleProperty.LABEL, "BigLinux Logo")` or set role to NONE |
| Settings card boxes | `theme_view.py:148` | Not focusable. Keyboard can't reach them | Ensure switch is in tab order; card click is supplementary |

### Test Checklist for Manual Verification

- [ ] Launch app with Orca running (`orca &; python main.py --test-mode`)
- [ ] Navigate entire livecd wizard using only Tab/Shift+Tab
- [ ] Verify Orca announces every step button with its step name
- [ ] Verify Orca announces each language item with name + native name
- [ ] Verify Orca announces keyboard layout options
- [ ] Navigate desktop layout view and verify Orca announces layout names
- [ ] Navigate theme view and verify Orca announces theme names
- [ ] Toggle JamesDSP switch and verify Orca announces "JamesDSP Audio, switch, on/off"
- [ ] Toggle contrast switch and verify Orca announces "Image quality, switch, on/off"
- [ ] Search for a language and verify Orca announces the search entry and filtered results
- [ ] Complete full wizard flow without looking at screen
- [ ] Verify error/warning messages are announced by Orca
- [ ] Test with Calamares app: verify all buttons, cards, and navigation are announced

---

## Accessibility Checklist (General)

- [ ] All interactive elements have accessible labels (CRITICAL — most do NOT currently)
- [ ] Keyboard navigation works for all flows (PARTIAL — FlowBox works, but settings cards need work)
- [ ] Color is never the only indicator (PARTIAL — step-completed/current/pending use only CSS styling, which may not convey state to color-blind users; consider adding checkmarks to completed steps)
- [ ] Text is readable at 2x font size (UNTESTED — hardcoded font sizes in CSS may break)
- [ ] Focus indicators are visible (OK — Adwaita's default focus ring is used)
- [ ] `@media (prefers-reduced-motion)` for CSS animations (MISSING — pulse animation on step icons)
- [ ] All images have alt text / accessible description (MISSING — logos, step icons, desktop previews)

---

## Tech Debt

### From Automated Tools

**Ruff Check (68 errors):**
- 65× E402 (imports after `gi.require_version()`) — acceptable for GTK pattern, suppress with `# noqa: E402`
- 2× F541 (f-string without placeholders) — fix
- 1× F401 (unused import) — fix

**Ruff Format:**
- 23 of 34 files need reformatting → Run `ruff format .`

**mypy:**
- 4 errors in livecd: 2× implicit Optional, 1× missing type annotation, 1× dynamic base class
- Calamares mypy blocked by duplicate module names (separate `main.py` files) — configure mypy per-project

**Vulture (dead code):**
- 21 unused variables (all from GTK signal callback parameters) — prefix with `_`

**Radon (complexity):**
- `_modify_settings_file`: CC=24 (grade D) — refactor urgently
- `ShellExecutor.execute`: CC=19 — consider simplification
- `_on_language_selected`: CC=12 (grade C) — split into sub-methods
- `InstallService.configure_installation`: CC=11 (grade C) — acceptable but monitor

**Tech Debt Markers:**
- 0 TODO/FIXME/HACK/XXX found — clean codebase

---

## Metrics (before)

```
Ruff:    68 errors (65 E402, 2 F541, 1 F401)
Format:  23/34 files need reformatting
mypy:    4 errors (livecd) + structural issues (calamares)
Vulture: 21 unused variables
Radon:   4 functions ≥ grade C (worst: CC=24, grade D)
         _modify_settings_file: D (24)
         ShellExecutor.execute: C (19)
         _on_language_selected: C (12)
         configure_installation: C (11)
Tests:   0 files, 0% coverage
A11y:    0 accessible labels on interactive widgets
```
