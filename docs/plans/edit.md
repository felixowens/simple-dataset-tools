# Image Edit Annotator Plan

## Analysis of Current Issues

The existing tool has several architectural and UX problems:

- Complex Flask architecture with multiple managers and convoluted routing
- Poor separation of concerns between frontend/backend
- Inefficient image handling with complex upload/serve logic
- Buggy state management in the JavaScript
- Outdated dependencies (Flask 2.3.3, old Pillow)
- Complex dataset management that adds unnecessary complexity
- Poor error handling and user feedback
