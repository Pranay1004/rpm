cmake_minimum_required(VERSION 3.20)
project(rpm_rt_engine CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find required packages
find_package(Boost 1.70 REQUIRED COMPONENTS system thread)

# Source files
set(SOURCES
    src/main.cpp
    src/hardware/serial_interface.cpp
    src/hardware/motor_controller.cpp
    src/hardware/sensor_reader.cpp
    src/control/rpm_controller.cpp
    src/safety/safety_monitor.cpp
)

# Create executable
add_executable(rpm_rt_engine ${SOURCES})

# Include directories
target_include_directories(rpm_rt_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${Boost_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(rpm_rt_engine PRIVATE
    ${Boost_LIBRARIES}
    pthread
)

# Compiler flags
if(MSVC)
    target_compile_options(rpm_rt_engine PRIVATE /W4 /WX)
else()
    target_compile_options(rpm_rt_engine PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# Testing
enable_testing()
add_subdirectory(tests)

# Install
install(TARGETS rpm_rt_engine DESTINATION bin)
