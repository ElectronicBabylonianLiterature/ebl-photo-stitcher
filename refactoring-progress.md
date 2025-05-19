# Refactoring Progress: EBL Photo Stitcher

## Files Refactored
1. `gui_workflow_runner.py` (271 lines) → Module: `workflow`
2. `stitch_processing_utils.py` (194 lines) → Module: `stitching`

## Modules Created

### Workflow Module
- **Created directory structure**: `workflow/domain`, `workflow/services`
- **Domain models**:
  - `WorkflowConfig` - Immutable configuration for the workflow
  - `RulerTemplates` - Immutable collection of ruler templates
  - `StepAllocation` - Progress allocation for different workflow steps
  - `WorkflowProgress` - Progress tracking for the workflow
  - `WorkflowResult` - Result information from workflow execution
- **Services**:
  - `FileOrganizer` - Handles organizing files into subfolders
  - `RulerHandler` - Handles ruler detection, extraction and processing 
  - `ArtifactProcessor` - Handles artifact extraction and processing
  - `ImageProcessor` - Handles image conversion and processing
  - `StitchCoordinator` - Handles the stitching process coordination
  - `WorkflowExecutor` - Orchestrates the entire workflow

### Stitching Module
- **Created directory structure**: `stitching/domain`, `stitching/services`
- **Domain models**:
  - `Dimension` - Represents image dimensions
  - `Position` - Represents coordinates on the canvas
  - `BoundingBox` - Represents a content bounding box
  - `BackgroundSettings` - Background configuration
  - `ResizeParams` - Parameters for resizing images
  - `StitchingConfig` - Configuration for stitching
  - `LayoutCoordinates` - Coordinates for layout positioning
  - `CanvasSize` - Size of the stitching canvas
  - `LogoSettings` - Configuration for logo placement
  - `ImageLayout` - Layout of images for stitching
- **Services**:
  - `image_resizer` - Handles image resizing operations
  - `layout_manager` - Manages layout calculation and positioning
  - `canvas_processor` - Processes the canvas (adding logos, cropping)
  - `StitchingService` - Facade providing a cohesive API for all stitching operations

## Improvements
- Each file is now less than 125 lines
- Code is more modular with single-responsibility services
- Using immutable objects with attrs for domain models
- Better separation of concerns with clean interfaces
- Improved error handling and resource management
- Consistent progress reporting
- Better testability through isolated components

## Improvements
- Each file is now less than 125 lines
- Code is more modular with single-responsibility services
- Using immutable objects with attrs for domain models
- Better separation of concerns with clean interfaces
- Improved error handling and resource management
- Consistent progress reporting
- Better testability through isolated components
- Added automated tests to verify refactored functionality

## Next Files to Refactor
1. `stitch_layout_manager.py` (156 lines)
2. `resize_ruler.py` (145 lines)
3. `object_extractor.py` (144 lines)
4. `raw_processor.py` (138 lines)
5. `ruler_detector.py` (134 lines)
6. `stitch_utils.py` (129 lines)
7. `stitch_output.py` (128 lines)

## Implementation Plan
1. Refactor the remaining large files one by one
2. Create comprehensive tests for each module
3. Remove all comments from Python files
4. Install and run linters to identify code smells


Please continue the refactoring. stitching.test_layout_manager works well, so no need to test it

To do:

- Fix Raw Processing
- Accept folder with subfolders

3. Implement a GUI for User-Defined Placement of Intermediate Photos for Complex Objects, with Gradient Mask Blending.
For objects represented by a large number of photos (e.g., more than the standard 2 for simple two-sided items or 6 for standard tablet views), provide a GUI where users can arrange thumbnails of these intermediate photos to define their layout for stitching. The GUI should look like similar to the attached design. Use Thumbnails to help the user determine the position of each photo. Each time a photo is added to the intermediary views, a new small rectangle is added between the outer side and the obverse/reverse.

The users should be able to define: 1) The obverse, reverse, left hand side, right hand side, top side and bottom side with only one photograph, and 2) additional sides to the left, right, top or bottom of the obverse and reverse, with one or more photos (they are arranged according to the order of selection).
Implement gradient masks for smoother blending between the intermediate photographs between obverse/reverse and the sides. This is how I used to do it in Photohsop: (1) Import image as new layer; (2) Select layer and click on Add layer mask; (3) Select the gradient tool and set colors to black-white. Draw a gradient on the layer
