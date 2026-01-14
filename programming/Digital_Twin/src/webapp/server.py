"""
RPM Digital Twin - Real-Time Web Dashboard Server
==================================================
SpaceX Dragon / Tesla Autopilot inspired UI backend.

Commercial-grade WebSocket streaming for live visualization.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from simulation import RPMSimulator, RPMGeometry, OperationMode


# =============================================================================
# DATA MODELS
# =============================================================================

class SimulationConfig(BaseModel):
    inner_rpm: float = 2.0
    outer_rpm: float = 2.0
    mode: str = "clinostat_3d"


class SimulationState(BaseModel):
    timestamp: float
    time_elapsed: float
    theta_inner_deg: float
    theta_outer_deg: float
    omega_inner_rpm: float
    omega_outer_rpm: float
    gravity_x: float
    gravity_y: float
    gravity_z: float
    instantaneous_g: float
    mean_g: float
    min_g: float
    max_g: float
    samples: int
    status: str


# =============================================================================
# APPLICATION
# =============================================================================

app = FastAPI(
    title="RPM Digital Twin",
    description="Commercial-grade Random Positioning Machine Control System",
    version="1.0.0"
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# SIMULATION ENGINE
# =============================================================================

class SimulationEngine:
    """Real-time simulation manager with WebSocket broadcasting."""
    
    def __init__(self):
        self.geometry = RPMGeometry(
            inner_frame_radius=0.15,
            outer_frame_radius=0.25,
            sample_mount_offset=np.array([0.0, 0.0, 0.10])
        )
        self.simulator = RPMSimulator(
            geometry=self.geometry,
            mode=OperationMode.CLINOSTAT_3D
        )
        
        self.running = False
        self.dt = 0.02  # 50 Hz simulation
        self.broadcast_rate = 20  # 20 Hz to clients
        
        # Metrics
        self.g_history: List[float] = []
        self.max_history = 3000  # 1 minute at 50Hz
        self.start_time = 0.0
        self.samples = 0
        
        # Connected clients
        self.clients: Set[WebSocket] = set()
        
        # Current config
        self.inner_rpm = 2.0
        self.outer_rpm = 2.0
        
        logger.info("Simulation engine initialized")
    
    def set_velocities(self, inner_rpm: float, outer_rpm: float):
        """Update target velocities."""
        self.inner_rpm = inner_rpm
        self.outer_rpm = outer_rpm
        omega_inner = inner_rpm * np.pi / 30
        omega_outer = outer_rpm * np.pi / 30
        self.simulator.set_velocities(omega_inner, omega_outer, unit="rad/s")
        logger.info(f"Velocities set: inner={inner_rpm} RPM, outer={outer_rpm} RPM")
    
    def start(self):
        """Start simulation."""
        self.running = True
        self.start_time = time.time()
        self.g_history.clear()
        self.samples = 0
        self.set_velocities(self.inner_rpm, self.outer_rpm)
        logger.info("Simulation started")
    
    def stop(self):
        """Stop simulation."""
        self.running = False
        logger.info("Simulation stopped")
    
    def reset(self):
        """Reset simulation state."""
        self.simulator = RPMSimulator(
            geometry=self.geometry,
            mode=OperationMode.CLINOSTAT_3D
        )
        self.g_history.clear()
        self.samples = 0
        self.start_time = time.time()
        self.set_velocities(self.inner_rpm, self.outer_rpm)
        logger.info("Simulation reset")
    
    def step(self) -> SimulationState:
        """Execute one simulation step."""
        state = self.simulator.step(self.dt)
        
        # Compute gravity in sample frame
        g_vec = self.simulator.gravity_calc.compute_gravity_in_sample_frame(
            state.theta_inner, state.theta_outer
        )
        g_mag = np.linalg.norm(g_vec) / 9.80665
        
        # Update history
        self.g_history.append(g_mag)
        if len(self.g_history) > self.max_history:
            self.g_history.pop(0)
        self.samples += 1
        
        # Compute statistics
        g_array = np.array(self.g_history)
        mean_g = float(np.mean(g_array))
        min_g = float(np.min(g_array))
        max_g = float(np.max(g_array))
        
        return SimulationState(
            timestamp=time.time(),
            time_elapsed=time.time() - self.start_time,
            theta_inner_deg=float(np.degrees(state.theta_inner)),
            theta_outer_deg=float(np.degrees(state.theta_outer)),
            omega_inner_rpm=float(state.omega_inner * 30 / np.pi),
            omega_outer_rpm=float(state.omega_outer * 30 / np.pi),
            gravity_x=float(g_vec[0]),
            gravity_y=float(g_vec[1]),
            gravity_z=float(g_vec[2]),
            instantaneous_g=float(g_mag),
            mean_g=mean_g,
            min_g=min_g,
            max_g=max_g,
            samples=self.samples,
            status="running" if self.running else "stopped"
        )
    
    async def broadcast(self, state: SimulationState):
        """Send state to all connected clients."""
        if not self.clients:
            return
        
        message = json.dumps(state.model_dump())
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)
        
        self.clients -= disconnected
    
    async def run_loop(self):
        """Main simulation loop with broadcasting."""
        broadcast_interval = 1.0 / self.broadcast_rate
        last_broadcast = 0.0
        
        while True:
            if self.running:
                state = self.step()
                
                now = time.time()
                if now - last_broadcast >= broadcast_interval:
                    await self.broadcast(state)
                    last_broadcast = now
                
                await asyncio.sleep(self.dt)
            else:
                await asyncio.sleep(0.1)


# Global simulation engine
engine = SimulationEngine()


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.on_event("startup")
async def startup():
    """Start simulation loop on server startup."""
    asyncio.create_task(engine.run_loop())
    logger.info("RPM Digital Twin server started")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main dashboard."""
    html_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(html_path)


@app.get("/api/status")
async def get_status():
    """Get current simulation status."""
    return {
        "running": engine.running,
        "inner_rpm": engine.inner_rpm,
        "outer_rpm": engine.outer_rpm,
        "samples": engine.samples,
        "clients": len(engine.clients)
    }


@app.post("/api/start")
async def start_simulation():
    """Start the simulation."""
    engine.start()
    return {"status": "started"}


@app.post("/api/stop")
async def stop_simulation():
    """Stop the simulation."""
    engine.stop()
    return {"status": "stopped"}


@app.post("/api/reset")
async def reset_simulation():
    """Reset the simulation."""
    engine.reset()
    return {"status": "reset"}


@app.post("/api/config")
async def update_config(config: SimulationConfig):
    """Update simulation configuration."""
    engine.set_velocities(config.inner_rpm, config.outer_rpm)
    return {"status": "updated", "config": config.model_dump()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await websocket.accept()
    engine.clients.add(websocket)
    logger.info(f"Client connected. Total clients: {len(engine.clients)}")
    
    try:
        while True:
            # Handle incoming commands
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "start":
                    engine.start()
                elif cmd.get("action") == "stop":
                    engine.stop()
                elif cmd.get("action") == "reset":
                    engine.reset()
                elif cmd.get("action") == "config":
                    engine.set_velocities(
                        cmd.get("inner_rpm", 2.0),
                        cmd.get("outer_rpm", 2.0)
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        engine.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(engine.clients)}")


# =============================================================================
# MAIN ENTRY
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
