import React from 'react';

export const ControlPanel: React.FC = () => {
  return (
    <div className="main-content">
      <h1 className="header-title">Motor Control</h1>
      <div className="panel">
        <h2 className="panel-title">Inner Frame Control</h2>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <button className="button button-primary">Start</button>
          <button className="button button-secondary">Stop</button>
          <button className="button button-danger">Emergency Stop</button>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title">Outer Frame Control</h2>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <button className="button button-primary">Start</button>
          <button className="button button-secondary">Stop</button>
          <button className="button button-danger">Emergency Stop</button>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
