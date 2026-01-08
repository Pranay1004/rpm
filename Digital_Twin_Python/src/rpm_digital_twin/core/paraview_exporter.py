"""
ParaView/VTK Export for RPM Digital Twin.

Exports collected data to VTK format for visualization in ParaView.
Includes trajectory export and automated post-processing scripts.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger


def export_to_vtk(
    timestamps: np.ndarray,
    trajectories: np.ndarray,
    gravity_vectors: np.ndarray,
    output_path: str = "rpm_data.vtk",
) -> str:
    """Export trajectory and field data to VTK format.
    
    Args:
        timestamps: (N,) time array
        trajectories: (N,3) spatial positions
        gravity_vectors: (N,3) gravity vectors
        output_path: output file path
    
    Returns:
        Path to created VTK file
    """
    filepath = Path(output_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    N = len(timestamps)
    
    with open(filepath, 'w') as f:
        # VTK header
        f.write("# vtk DataFile Version 3.0\n")
        f.write("RPM Trajectory and Gravity Field\n")
        f.write("ASCII\n")
        f.write("DATASET POLYDATA\n")
        
        # Points (trajectory)
        f.write(f"POINTS {N} float\n")
        for traj in trajectories:
            f.write(f"{traj[0]:.6f} {traj[1]:.6f} {traj[2]:.6f}\n")
        
        # Lines (trajectory path)
        f.write(f"LINES {N-1} {3*(N-1)}\n")
        for i in range(N-1):
            f.write(f"2 {i} {i+1}\n")
        
        # Point data (gravity vectors)
        f.write(f"POINT_DATA {N}\n")
        f.write("VECTORS gravity_field float\n")
        for grav in gravity_vectors:
            f.write(f"{grav[0]:.6f} {grav[1]:.6f} {grav[2]:.6f}\n")
        
        # Scalars (time)
        f.write("SCALARS time float\n")
        f.write("LOOKUP_TABLE default\n")
        for t in timestamps:
            f.write(f"{t:.6f}\n")
    
    logger.info(f"Exported {N} points to {filepath}")
    return str(filepath)


def generate_paraview_script(
    input_vtk: str,
    output_path: str = "rpm_visualization.py",
) -> str:
    """Generate a Python script for ParaView automation.
    
    Creates a ParaView Python script that can be run to automatically
    create publication-quality visualizations.
    """
    script_content = f'''#!/usr/bin/env python3
"""ParaView visualization script for RPM data - Auto-generated"""

import paraview
paraview.compatibility.major = 5
paraview.compatibility.minor = 10

from paraview.simple import *

# Load data
reader = OpenDataFile('{input_vtk}')
RenderView1 = GetActiveViewOrCreate('RenderView')

# Display geometry
display = Show(reader, RenderView1)
display.Representation = 'Surface'
display.ColorArrayName = ['POINTS', 'time']

# Color by time
colorTF = GetColorTransferFunction('time')
colorTF.ApplyPreset('Viridis')

# Reset view
RenderView1.ResetCamera()
RenderView1.ViewSize = [1200, 900]

# Save screenshot
SaveScreenshot('{input_vtk.replace(".vtk", "_screenshot.png")}', 
               RenderView1, ImageResolution=[1200, 900])

# Export as state file
SaveState('{input_vtk.replace(".vtk", "_state.pvsm")}')

print(f"Visualization complete: saved to {{RenderView1}}")
'''
    
    filepath = Path(output_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        f.write(script_content)
    
    filepath.chmod(0o755)
    logger.info(f"Generated ParaView script: {filepath}")
    return str(filepath)


def export_trajectory_pvtu(
    timestamps: np.ndarray,
    positions: np.ndarray,
    velocities: np.ndarray,
    output_base: str = "rpm_trajectory",
) -> str:
    """Export as unstructured grid (PVTU) for parallel visualization.
    
    This is a simplified XML format version.
    """
    filepath = Path(output_base).with_suffix('.vtu')
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    N = len(timestamps)
    
    # Simple XML-based VTU format
    xml = f'''<?xml version="1.0"?>
<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">
  <UnstructuredGrid>
    <Piece NumberOfPoints="{N}" NumberOfCells="{N-1}">
      <Points>
        <DataArray type="Float32" NumberOfComponents="3" format="ascii">
'''
    
    for pos in positions:
        xml += f"          {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}\n"
    
    xml += '''        </DataArray>
      </Points>
      <Cells>
        <DataArray type="Int32" Name="connectivity" format="ascii">
'''
    
    for i in range(N-1):
        xml += f"          {i} {i+1}\n"
    
    xml += '''        </DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">
'''
    for i in range(1, N):
        xml += f"          {i*2}\n"
    
    xml += '''        </DataArray>
        <DataArray type="UInt8" Name="types" format="ascii">
'''
    for _ in range(N-1):
        xml += "          3\n"  # VTK_LINE
    
    xml += f'''        </DataArray>
      </Cells>
      <PointData>
        <DataArray type="Float32" Name="time" format="ascii">
'''
    
    for t in timestamps:
        xml += f"          {t:.6f}\n"
    
    xml += f'''        </DataArray>
        <DataArray type="Float32" Name="velocity" NumberOfComponents="3" format="ascii">
'''
    
    for vel in velocities:
        xml += f"          {vel[0]:.6f} {vel[1]:.6f} {vel[2]:.6f}\n"
    
    xml += '''        </DataArray>
      </PointData>
    </Piece>
  </UnstructuredGrid>
</VTKFile>
'''
    
    with open(filepath, 'w') as f:
        f.write(xml)
    
    logger.info(f"Exported VTU: {filepath}")
    return str(filepath)


def export_to_csv_for_paraview(
    data_dict: dict,
    output_path: str = "rpm_data.csv",
) -> str:
    """Export data to CSV compatible with ParaView.
    
    CSV format: timestamp, x, y, z, gx, gy, gz, ax, ay, az
    """
    filepath = Path(output_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    import csv
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 
            'pos_x', 'pos_y', 'pos_z',
            'gravity_x', 'gravity_y', 'gravity_z',
            'accel_x', 'accel_y', 'accel_z',
        ])
        
        n = data_dict.get('timestamps', np.array([])).shape[0]
        for i in range(n):
            ts = data_dict['timestamps'][i] if 'timestamps' in data_dict else 0
            pos = data_dict['positions'][i] if 'positions' in data_dict else [0,0,0]
            g = data_dict['gravity'][i] if 'gravity' in data_dict else [0,0,0]
            a = data_dict['acceleration'][i] if 'acceleration' in data_dict else [0,0,0]
            
            writer.writerow([ts, pos[0], pos[1], pos[2], g[0], g[1], g[2], a[0], a[1], a[2]])
    
    logger.info(f"Exported CSV: {filepath}")
    return str(filepath)
