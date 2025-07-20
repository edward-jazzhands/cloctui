# CLOCTUI Changelog

## 0.2.3 - (2025-07-19)

- Refactored app again to push a new screen every time the group mode is changed. This was necessary to fix the issue with the table not resizing properly when switching between group modes.
- Implemented logic in python to dynamically set the maximum height for the table based on the terminal size.
- Set background to transparent and turned ansi_color to True in the app class.
- Changed button style to transparent buttons.

## 0.2.2 - (2025-07-19)

- Made check for CLOC installation run before empty path check.

## 0.2.1 - (2025-07-19)

- Fixed all visual issues with more container magic.
- Implemented proper table resizing with min/max values.
- Fixed sorting logic to work after amount of columns is changed.
- Added quit buttons for both clearing and not clearing the screen.

## 0.2.0 - (2025-07-19)

- Big refactor of the app
- Added keyboard controls
- Added nice check for CLOC and error message if not installed
- Added grouping by language
- Added grouping by file type
- Added option for fullscreen or inline mode in CLI (-f flag)

## 0.1.0 - (2025-07-12)

- Released version 0.1.0 of CLOCTUI.
