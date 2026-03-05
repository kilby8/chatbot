# Site2CAD (v2)

Convert site photos into a sparse 3D model and export CAD-friendly geometry.

## What this app does

- Upload multiple site photos (`.jpg`, `.jpeg`, `.png`)
- Reconstruct a sparse 3D point cloud using multi-view geometry (OpenCV)
- Post-process points for CAD use:
  - ground alignment (PCA)
  - outlier filtering
  - percentile trimming
  - optional scale-to-known-dimension
- Build a quick mesh from the cleaned point cloud (convex hull)
- Export outputs:
  - `PLY` (point cloud)
  - `OBJ` (mesh)
  - `DXF` (3D geometry)
  - `DXF floorplan` (2D footprint hull)
- Show pair-by-pair reconstruction quality, post-processing report, and XY/XZ/YZ projections

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

## SSH into a remote server (secure setup)

If you are deploying this app on an Ubuntu/Debian host and want SSH access:

1. Copy your public key to the host or provide it inline.
2. Run:

   ```bash
   APP_USER=ubuntu PUBLIC_KEY_FILE=~/.ssh/id_ed25519.pub ./scripts/setup_ssh_access.sh
   ```

   Or:

   ```bash
   APP_USER=ubuntu PUBLIC_KEY_VALUE="ssh-ed25519 AAAA... your@email" ./scripts/setup_ssh_access.sh
   ```

3. Connect:

   ```bash
   ssh ubuntu@<SERVER_PUBLIC_IP>
   ```

4. Tunnel Streamlit from remote host to your machine:

   ```bash
   ssh -L 8501:localhost:8501 ubuntu@<SERVER_PUBLIC_IP>
   ```

   Then open `http://localhost:8501`.

## Capture tips for better results

- Use 6-30 photos with 60-80% overlap.
- Walk around the target area in sequence.
- Avoid motion blur and major exposure changes between images.
- Include textured objects/surfaces; plain walls are difficult to reconstruct.

## Accuracy notes

This is still a lightweight photogrammetry pipeline. For production-grade survey/CAD accuracy, add:

- camera calibration with known intrinsics,
- control points or known distances,
- dense reconstruction,
- post-processing in CAD/BIM tools.
