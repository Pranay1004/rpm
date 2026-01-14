enable_testing()

# Test executable
add_executable(rpm_rt_engine_tests
    motor_controller_test.cpp
)

target_include_directories(rpm_rt_engine_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

add_test(NAME MotorControllerTests COMMAND rpm_rt_engine_tests)
