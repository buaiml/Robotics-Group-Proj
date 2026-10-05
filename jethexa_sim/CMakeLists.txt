cmake_minimum_required(VERSION 3.8)
project(jethexa_sim)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf worlds launch config
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/stand.py
    scripts/check_model.py
    scripts/ik_demo.py
    scripts/drop_box.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
