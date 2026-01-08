clc;
clear all;

% RPM_SIMULATION.M
%
% MATLAB script to simulate the kinematics and effective gravity
% of a two-axis Random Positioning Machine (RPM).
% The design uses two orthogonal rotation axes (Outer Frame: Z-axis, Inner Frame: Y-axis).
% The goal is to show how the effective gravity (g_rms) is reduced over time.

%% 1. System Parameters and Initial Conditions

% Time parameters
T_end = 600;        % Total simulation time (s) - 10 minutes
dt = 0.01;          % Time step (s)
time = 0:dt:T_end;  % Time vector
N = length(time);   % Number of steps

% Physical Constants
g_mag = 9.81;       % Magnitude of gravity (m/s^2)
g_inertial = [0; -g_mag; 0]; % Gravity vector in the Inertial (Lab) frame (assuming Y is 'up/down')

% Motor / Kinematic Constraints (from document analysis)
N_max_rpm = 10;
w_max = N_max_rpm * (2 * pi / 60); % Max Angular Velocity (1.047 rad/s)
alpha_max = 10;                    % Max Angular Acceleration (10 rad/s^2)

% Inertial Properties (Used only for motor torque calculation, but kept here for completeness)
I_outer = 0.614;    % IZZ of Outer Frame (kg*m^2)
I_inner = 0.172;    % IYY of Inner Frame (kg*m^2)

% Sample Point of Interest (r)
% The centripetal acceleration (a = w^2 * r) is the main residual gravity source.
% We define a point r on the edge of the payload to calculate the maximum residual acceleration.
% Assuming payload is 180x180x180 mm (from Polycarbonate sheets: 180x180x20*4=80mm thick, assume cube for simplicity)
r_mag = 0.10; % Distance from the center of rotation to a point on the sample (m)
r_payload_initial = [r_mag; 0; 0]; % A point on the payload's X-axis

%% 2. Initialization

% Reset persistent state of the motor controller function for a clean simulation run
clear random_motor_controller;

% Angular Positions (rad)
theta1 = zeros(N, 1); % Outer Frame (Rotation around Z-axis)
theta2 = zeros(N, 1); % Inner Frame (Rotation around Y-axis)

% Angular Velocities (rad/s) - Initialized using the random controller
w1 = zeros(N, 1);
w2 = zeros(N, 1);

% Results storage
g_payload_components = zeros(3, N); % Instantaneous gravity vector in the payload frame
a_centripetal_components = zeros(3, N); % Instantaneous centripetal acceleration in payload frame
r_payload_history = zeros(3, N); % Position of the sample point in the inertial frame

%% 3. Simulation Loop

disp('Starting RPM Kinematics Simulation...');

for i = 2:N
    % --- Step 1: Generate random angular velocities ---
    % Calls the helper function to determine the next angular velocity, bounded by w_max
    [w1(i), w2(i)] = random_motor_controller(w1(i-1), w2(i-1), dt, w_max, alpha_max);

    % --- Step 2: Update Angular Positions (Integration) ---
    theta1(i) = theta1(i-1) + w1(i) * dt;
    theta2(i) = theta2(i-1) + w2(i) * dt;

    % Normalize angles to keep them manageable (optional, but good practice)
    theta1(i) = mod(theta1(i), 2*pi);
    theta2(i) = mod(theta2(i), 2*pi);

    % --- Step 3: Define Rotation Matrices ---
    % R1: Rotation of Outer Frame about Inertial Z-axis (Yaw)
    R1 = [cos(theta1(i)), -sin(theta1(i)), 0;
          sin(theta1(i)),  cos(theta1(i)), 0;
          0,               0,              1];

    % R2: Rotation of Inner Frame about Local Y-axis (Pitch)
    % Note: The Inner Frame's Y-axis is defined relative to the Outer Frame.
    R2 = [cos(theta2(i)), 0, sin(theta2(i));
          0,              1, 0;
          -sin(theta2(i)), 0, cos(theta2(i))];

    % R_total: Total rotation matrix from Payload frame to Inertial (Lab) frame
    % R_total = R1 * R2
    R_total = R1 * R2;

    % --- Step 4: Calculate Gravity Vector in Payload Frame ---
    % g_payload = R_total' * g_inertial
    % This is the component of acceleration due to gravity on the sample
    g_payload = R_total' * g_inertial;
    g_payload_components(:, i) = g_payload;

    % --- Step 5: Calculate Centripetal Acceleration (Residual G) ---
    % Centripetal acceleration (a_c = omega x (omega x r)) is the main source of residual g.
    % We use the total angular velocity vector in the payload frame (w_p)
    % The total angular velocity vector in the Inertial frame (w_i) is:
    % w_i = w1_z_i + w2_y_i, where w2_y_i = R1 * [0; w2; 0] (y-axis of frame 1)
    w1_i = [0; 0; w1(i)];
    w2_i = R1 * [0; w2(i); 0];
    w_i = w1_i + w2_i;

    % Total angular velocity in the Payload frame (w_p)
    w_p = R_total' * w_i;
    
    % Centripetal acceleration (a_c = -w_p x (w_p x r_payload_initial))
    % The centripetal acceleration is the main component of RESIDUAL g in an RPM.
    % We use the negative sign because the acceleration vector points inward.
    a_centripetal = -cross(w_p, cross(w_p, r_payload_initial));
    a_centripetal_components(:, i) = a_centripetal;
    
    % Track the sample point in the inertial frame for visualization
    r_payload_history(:, i) = R_total * r_payload_initial;
end

disp('Simulation Complete.');

%% 4. Analysis and Results

% --- IMPORTANT: Microgravity in RPMs is achieved by two effects ---

% 1. TIME-AVERAGED GRAVITY (The main effect)
% The instantaneous gravity vector components in the payload frame average to near zero.
g_avg_vector = mean(g_payload_components, 2);
g_avg_mag = norm(g_avg_vector);

% 2. CENTRIPETAL ACCELERATION (The main residual effect)
% This is the acceleration required to keep the sample moving in a circle.
% We typically quantify the residual g by the RMS or MAX centripetal acceleration.
a_centripetal_mag = vecnorm(a_centripetal_components);
a_centripetal_rms = rms(a_centripetal_mag);
a_centripetal_max = max(a_centripetal_mag);


% Calculate Total Instantaneous Acceleration for Plotting
% The instantaneous acceleration on the point due to both gravity and rotation
a_total_instantaneous = g_payload_components + a_centripetal_components;
a_mag_total = vecnorm(a_total_instantaneous);
a_total_instantaneous_rms = rms(a_mag_total); % This will still be close to 1g due to instantaneous gravity

disp(' ');
disp('----------------------------------------------------');
fprintf('Total Simulation Time: %d seconds\n', T_end);
fprintf('Max Motor Speed: %.1f RPM\n', N_max_rpm);
fprintf('Sample Distance from Center (r): %.2f m\n', r_mag);
disp(' ');
disp('--- Microgravity Performance Metrics ---');
fprintf('1. Time-Averaged Gravity Vector Magnitude: %.2e g\n', g_avg_mag / g_mag);
fprintf('   (Goal: Close to zero. This shows success in gravity vector randomization.)\n');
fprintf('2. Centripetal Residual G (RMS): %.4f g\n', a_centripetal_rms / g_mag);
fprintf('3. Centripetal Residual G (MAX): %.4f g\n', a_centripetal_max / g_mag);
fprintf('   (Metric for microgravity quality. Typically aimed for < 0.01g)\n');
disp('----------------------------------------------------');


%% 5. Visualization

figure('Color', 'w');

% Subplot 1: Angular Velocities
subplot(3, 1, 1);
plot(time, w1, 'LineWidth', 2, 'DisplayName', 'Outer Frame (\omega_1)');
hold on;
plot(time, w2, 'LineWidth', 2, 'DisplayName', 'Inner Frame (\omega_2)');
title('Motor Angular Velocity Profiles');
ylabel('Angular Velocity (rad/s)');
legend('show', 'Location', 'best');
grid on;

% Subplot 2: Gravity Vector Components in Payload Frame
subplot(3, 1, 2);
plot(time, g_payload_components(1, :) / g_mag, 'LineWidth', 2, 'DisplayName', 'g_x');
hold on;
plot(time, g_payload_components(2, :) / g_mag, 'LineWidth', 2, 'DisplayName', 'g_y');
plot(time, g_payload_components(3, :) / g_mag, 'LineWidth', 2, 'DisplayName', 'g_z');
title('Instantaneous Gravity Vector in Payload Frame (g_i)');
ylabel('Gravity Component (g)');
legend('show', 'Location', 'best');
grid on;

% Subplot 3: Total Effective Acceleration (The two residual components)
subplot(3, 1, 3);
plot(time, a_centripetal_mag / g_mag, 'LineWidth', 2, 'DisplayName', 'Centripetal Acceleration (a_c)');
hold on;
plot(time, a_mag_total / g_mag, 'LineWidth', 2, 'DisplayName', 'Total Instantaneous Acceleration');
% Add a horizontal line to show the 1g baseline for perspective
yline(1.0, 'r--', '1 g Baseline', 'LineWidth', 1, 'HandleVisibility', 'off');
title(sprintf('Residual Acceleration Components (Residual RMS: %.4f g)', a_centripetal_rms / g_mag));
xlabel('Time (s)');
ylabel('Acceleration (g)');
legend('show', 'Location', 'southoutside');
grid on;


% 3D Visualization of the Sample Point's Trajectory in the Inertial Frame
figure('Color', 'w');
plot3(r_payload_history(1, :), r_payload_history(2, :), r_payload_history(3, :), 'b-', 'LineWidth', 0.5);
hold on;
plot3(r_payload_history(1, 1), r_payload_history(2, 1), r_payload_history(3, 1), 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r', 'DisplayName', 'Start');
plot3(0, 0, 0, 'kx', 'MarkerSize', 10, 'LineWidth', 2, 'DisplayName', 'Center of Rotation');
xlabel('X (m)');
ylabel('Y (m) - Gravity Axis');
zlabel('Z (m)');
title('3D Trajectory of a Sample Point in the Inertial Frame');
axis equal;
grid on;
view(3); % Set a 3D view