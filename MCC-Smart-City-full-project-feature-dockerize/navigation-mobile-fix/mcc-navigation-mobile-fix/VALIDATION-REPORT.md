# MCC Navigation + Mobile Sidebar Fix Validation

Source basis: current `navigation-mobile-current-state.txt` supplied 2026-08-17.

## Root cause confirmed
- The desktop sidebar uses `hidden ... lg:flex`, so it intentionally disappears below the `lg` breakpoint.
- The TopBar hamburger button was rendered below `lg`, but had no `onClick` handler or shared open/closed state.
- The navigation seed did not include `/devices`, so Camera & Device Management could not appear in the dynamic Operations group.

## Changes
- Dashboard layout now owns responsive sidebar state.
- Hamburger toggles the mobile drawer.
- Mobile sidebar includes backdrop and close button.
- Clicking a navigation link or changing route closes the drawer.
- Desktop sidebar remains permanently visible at `lg` and above.
- Added `Camera & Devices` -> `/devices` to Operations, sort order 5, permission `cameras.view`.
- `/devices` TopBar title updated to `Camera & Device Management`.

## Static validation performed
- Python `py_compile`: PASS for `app/db/init_db.py`.
- TypeScript compiler `transpileModule`: PASS for layout.tsx, sidebar.tsx, top-bar.tsx.
- Navigation insertion check: PASS.

## Runtime acceptance still required in the user's Docker repo
1. Rebuild/restart backend so `init_db()` seeds `/devices`.
2. Rebuild/recreate frontend.
3. Verify Operations shows Camera & Devices.
4. Verify desktop sidebar still behaves normally.
5. Resize/split screen below `lg`, click hamburger, verify drawer opens.
6. Verify backdrop, X button, and navigation links close the drawer.
