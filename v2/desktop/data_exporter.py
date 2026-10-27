"""
Scientific Data Exporter for RPM Digital Twin.
Generates publication-quality RFC-4180 CSV logs and vector plot figures.
"""

from datetime import datetime
import os
from typing import Any, Dict, List
import numpy as np


class ScientificDataExporter:
    """
    Handles CSV telemetry export and high-resolution figure saving.
    """

    @staticmethod
    def export_telemetry_csv(
        filepath: str,
        records: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Exports simulation/hardware records to standard scientific CSV.
        """
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            # Metadata Header
            f.write("# =====================================================================\n")
            f.write("# INDIAN INSTITUTE OF SPACE SCIENCE AND TECHNOLOGY (IIST)\n")
            f.write("# Department of Aerospace Engineering - Microgravity Simulation Laboratory\n")
            f.write("# Project: Random Positioning Machine (RPM) Digital Twin v2.0\n")
            f.write(f"# Date & Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            for k, v in metadata.items():
                f.write(f"# {k}: {v}\n")
            f.write("# =====================================================================\n")
            f.write("#\n")
            
            # Column headers
            headers = [
                "time_s",
                "phi_deg",
                "psi_deg",
                "omega_phi_rpm",
                "omega_psi_rpm",
                "alpha_phi_rad_s2",
                "alpha_psi_rad_s2",
                "gx_g",
                "gy_g",
                "gz_g",
                "inst_g",
                "taSMG_g",
                "centrifugal_edge_g",
                "euler_edge_g",
                "wall_shear_stress_mPa",
                "telemetry_residual_g"
            ]
            f.write(",".join(headers) + "\n")
            
            # Data rows
            for r in records:
                row = [
                    f"{r.get('timestamp', 0.0):.3f}",
                    f"{r.get('phi_deg', 0.0):.2f}",
                    f"{r.get('psi_deg', 0.0):.2f}",
                    f"{r.get('omega_phi_rpm', 0.0):.3f}",
                    f"{r.get('omega_psi_rpm', 0.0):.3f}",
                    f"{r.get('alpha_phi_rad_s2', 0.0):.4f}",
                    f"{r.get('alpha_psi_rad_s2', 0.0):.4f}",
                    f"{r.get('gx', 0.0):.4f}",
                    f"{r.get('gy', 0.0):.4f}",
                    f"{r.get('gz', 0.0):.4f}",
                    f"{r.get('instant_g', 0.0):.4f}",
                    f"{r.get('taSMG', 0.0):.5f}",
                    f"{r.get('centrifugal_edge_g', 0.0):.5f}",
                    f"{r.get('euler_edge_g', 0.0):.5f}",
                    f"{r.get('shear_stress_mPa', 0.0):.2f}",
                    f"{r.get('telemetry_residual_g', ''):}"
                ]
                f.write(",".join(row) + "\n")

        return filepath
