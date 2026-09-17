"""Bring up Gazebo Classic with the JetHexa spawned on flat ground.

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
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = get_package_share_directory("jethexa_sim")

    gui = LaunchConfiguration("gui")
    world = LaunchConfiguration("world")
    spawn_z = LaunchConfiguration("spawn_z")

    robot_description = Command([
        "xacro ", PathJoinSubstitution([FindPackageShare("jethexa_sim"), "urdf", "jethexa.urdf.xacro"]),
    ])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("gazebo_ros"), "launch", "gazebo.launch.py")
        ),
        launch_arguments={
            "world": world,
            "gui": gui,
            "verbose": "false",
        }.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
    )

    spawn = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=["-topic", "robot_description", "-entity", "jethexa", "-z", spawn_z],
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
            default_value=os.path.join(pkg, "worlds", "flat_ground.world"),
        ),
        gazebo,
        robot_state_publisher,
        spawn,
        # Controllers must not be spawned before the entity exists.
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[load_jsb])),
        RegisterEventHandler(OnProcessExit(target_action=load_jsb, on_exit=[load_positions])),
        rviz,
    ])
