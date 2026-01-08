cmake_minimum_required(VERSION 3.20)
project(rpm_digital_twin_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(rpm_digital_twin_cpp
  src/main.cpp
  src/math.cpp
  src/numerical.cpp
  src/live.cpp
  src/csv.cpp
  src/stats.cpp
)

target_include_directories(rpm_digital_twin_cpp PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

if(APPLE)
  target_compile_definitions(rpm_digital_twin_cpp PRIVATE RPMDT_APPLE=1)
endif()
