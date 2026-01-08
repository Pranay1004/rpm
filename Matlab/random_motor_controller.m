function [w_next1, w_next2] = random_motor_controller(w_curr1, w_curr2, dt, w_max, alpha_max)
% RANDOM_MOTOR_CONTROLLER
%   Generates the next angular velocity for the two RPM motors.
%   It simulates a random positioning strategy by randomly deciding when to
%   change the acceleration direction.
%
% Inputs:
%   w_curr1, w_curr2: Current angular velocities (rad/s)
%   dt: Time step (s)
%   w_max: Maximum angular velocity (rad/s)
%   alpha_max: Maximum angular acceleration (rad/s^2)
%
% Outputs:
%   w_next1, w_next2: Next angular velocities (rad/s)

    % Define the probability of changing the acceleration direction in this time step (e.g., 0.1% chance)
    P_change = 0.001;
    
    % --- Motor 1 (Outer Frame) Control ---
    persistent alpha1 % Persistent variable to store the current acceleration for smooth transitions
    % Check if this is the first call, or if the calling script wants to reset the persistent state
    if isempty(alpha1)
        alpha1 = alpha_max * (2*rand() - 1); % Initial random acceleration
    end

    % Randomly decide if the acceleration direction should change
    if rand() < P_change
        % Change acceleration to a new random value, bounded by alpha_max
        alpha1 = alpha_max * (2*rand() - 1);
    end

    % Calculate next velocity
    w_next1 = w_curr1 + alpha1 * dt;
    
    % Check for velocity limits and adjust if needed
    if w_next1 > w_max
        w_next1 = w_max;
        alpha1 = -alpha_max; % Reverse acceleration if hitting positive limit
    elseif w_next1 < -w_max
        w_next1 = -w_max;
        alpha1 = alpha_max;  % Reverse acceleration if hitting negative limit
    end
    
    % --- Motor 2 (Inner Frame) Control ---
    persistent alpha2
    if isempty(alpha2)
        alpha2 = alpha_max * (2*rand() - 1);
    end

    if rand() < P_change
        alpha2 = alpha_max * (2*rand() - 1);
    end
    
    w_next2 = w_curr2 + alpha2 * dt;

    if w_next2 > w_max
        w_next2 = w_max;
        alpha2 = -alpha_max;
    elseif w_next2 < -w_max
        w_next2 = -w_max;
        alpha2 = alpha_max;
    end
end