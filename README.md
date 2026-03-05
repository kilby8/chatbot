# Site2CAD (MVP)

Convert site photos into a sparse 3D reconstruction and export CAD-friendly files.

## What this app does

- Upload multiple site photos (`.jpg`, `.jpeg`, `.png`)
- Reconstruct a sparse 3D point cloud using multi-view geometry (OpenCV)
- Build a quick mesh from the point cloud (convex hull)
- Export outputs:
  - `PLY` (point cloud)
  - `OBJ` (mesh)
  - `DXF` (CAD-friendly geometry)
- Show pair-by-pair reconstruction quality and 2D projections of the generated 3D points

## Run locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Start the app:

   ```bash
   streamlit run streamlit_app.py
   ```

3. Open the Streamlit URL, upload photos, tune settings, and run reconstruction.

## Capture tips for better results

- Use 6-30 photos with 60-80% overlap.
- Walk around the target area in sequence.
- Avoid motion blur and major exposure changes between images.
- Include textured objects/surfaces; plain walls are difficult to reconstruct.

## Accuracy note

This is an MVP reconstruction pipeline with approximate scale based on your camera step estimate.
For production-grade survey/CAD accuracy, add:

- camera calibration with known intrinsics,
- control points or known distances,
- dense reconstruction,
- post-processing in CAD/BIM tools.
