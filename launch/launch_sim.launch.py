import os
from ament_index_python.packages import get_package_share_directory

from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    package_name = 'grad-project'

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory(package_name),
                         'launch', 'rsp.launch.py')
        ]),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare(package_name),
            'config',
            'my_controllers.yaml',
        ]
    )

#    twist_mux_params = os.path.join(
#        get_package_share_directory(package_name), 'config', 'twist_mux.yaml'
#    )
#    twist_mux = Node(
#        package='twist_mux',
#        executable='twist_mux',
#        parameters=[twist_mux_params, {'use_sim_time': True}],
#        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel_unstamped')]
#    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name',
                   'amr', '-allow_renaming', 'true', '-z', '0.1'],
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )
    
    diff_drive_base_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'diff_drive_base_controller',
            '--param-file',
            robot_controllers,
            '--controller-ros-args',
            '-r /diff_drive_base_controller/cmd_vel:=/cmd_vel',
        ],
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    camera_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    world_file = os.path.join(
        get_package_share_directory(package_name), 'worlds', 'obstacles.world'
    )

    ld = LaunchDescription([
        rsp,
        #twist_mux,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [PathJoinSubstitution([FindPackageShare('ros_gz_sim'),
                                       'launch',
                                       'gz_sim.launch.py'])]),
            launch_arguments=[('gz_args', [f' -r -v 1 empty.sdf']), ('on_exit_shutdown', 'true')]),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[joint_state_broadcaster_spawner],
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[diff_drive_base_controller_spawner],
            )
        ),
        clock_bridge,
        spawn_entity,
        camera_bridge,
    ])
    return ld
