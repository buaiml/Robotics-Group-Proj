"""Bring up Gazebo Harmonic with the JetHexa spawned on flat ground.

    ros2 launch jethexa_sim jethexa_gazebo.launch.py
    ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false   # headless
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = get_package_share_directory("jethexa_sim")

    gui = LaunchConfiguration("gui")
    world = LaunchConfiguration("world")
    spawn_z = LaunchConfiguration("spawn_z")

    # ParameterValue(..., value_type=str) is required: without it the launch
    # system tries to parse the generated URDF as YAML and dies.
    robot_description = ParameterValue(
        Command([
            "xacro ",
            PathJoinSubstitution([FindPackageShare("jethexa_sim"), "urdf", "jethexa.urdf.xacro"]),
        ]),
        value_type=str,
    )

    # -r starts the world unpaused; -s runs the server only (no GUI).
    gz_args = PythonExpression([
        "'-r -v 3 ' + '", world, "' if '", gui, "' == 'true' else '-r -s -v 3 ' + '", world, "'",
    ])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": gz_args}.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
    )

    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "robot_description", "-name", "jethexa", "-z", spawn_z],
        output="screen",
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["--ros-args", "-p", f"config_file:={os.path.join(pkg, 'config', 'gz_bridge.yaml')}"],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    load_jsb = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    load_positions = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_group_position_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        condition=IfCondition(LaunchConfiguration("rviz")),
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("rviz", default_value="false"),
        DeclareLaunchArgument("spawn_z", default_value="0.15"),
        DeclareLaunchArgument(
            "world",
            default_value=os.path.join(pkg, "worlds", "flat_ground.sdf"),
        ),
        gazebo,
        robot_state_publisher,
        spawn,
        bridge,
        # Controllers must not be spawned before the entity exists.
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[load_jsb])),
        RegisterEventHandler(OnProcessExit(target_action=load_jsb, on_exit=[load_positions])),
        rviz,
    ])
