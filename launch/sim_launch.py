import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue 

def generate_launch_description():

    # 1. Fetch Package Directories
    pkg_grad_project = get_package_share_directory('grad-project')
    pkg_esp32_streamer = get_package_share_directory('esp32_camera_streamer')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    # 2. File Paths Configuration
    xacro_file = os.path.join(pkg_grad_project, 'description', 'robot.urdf.xacro')
    ekf_params_file = os.path.join(pkg_grad_project, 'config', 'ekf.yaml')
    map_yaml_file = os.path.join(pkg_grad_project, 'maps', 'room_map.yaml')
    nav2_params_file = os.path.join(pkg_grad_project, 'config', 'nav2_params.yaml')
    twist_mux_params_file = os.path.join(pkg_grad_project, 'config', 'twist_mux.yaml')
    rviz_config_file = os.path.join(pkg_grad_project, 'config', 'default.rviz')
    world_file = os.path.join(pkg_grad_project, 'worlds', 'obstacles.world')

    # 3. Launch Configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_description_raw = Command(['xacro ', xacro_file, ' sim_mode:=', use_sim_time])
    robot_description_param = ParameterValue(robot_description_raw, value_type=str)
    params = {'robot_description': robot_description_param, 'use_sim_time': use_sim_time}

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU'
            ],
        remappings=[
            ('/imu', '/imu/data')
        ],
        output='screen'
    )

    return LaunchDescription([
        # Declare Simulation Time Argument
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        
        # Gazebo Server & Client Launch
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'gz_args': f'-r {world_file}'}.items()
        ),

        # 2. Spawn Robot in Gazebo
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=['-topic', 'robot_description', '-name', 'my_robot'],
            output='screen'
        ),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[params]
        ),

        # Twist Mux Node
        Node(
            package='twist_mux',
            executable='twist_mux',
            name='twist_mux',
            output='screen',
            parameters=[twist_mux_params_file, {'use_sim_time': use_sim_time}],
            remappings=[
                ('/cmd_vel_out', '/cmd_vel')
            ]
        ),

        # ArUco Detector Node (Configured for DICT_5X5_50)
        Node(
            package='esp32_camera_streamer',
            executable='aruco_detector_node',
            name='aruco_detector_node',
            output='screen',
            parameters=[{
                'marker_size': 0.10,
                'dictionary_name': 'DICT_5X5_50',
                'use_sim_time': use_sim_time
            }]
        ),

        # Static Transforms for Map Markers
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_0',
            arguments=['0.0', '0.0', '0.2', '0.0', '0.0', '0.0', 'map', 'marker_frame_0']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_1',
            arguments=['2.0', '0.0', '0.2', '1.5708', '0.0', '0.0', 'map', 'marker_frame_1']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_2',
            arguments=['2.0', '2.0', '0.2', '3.14159', '0.0', '0.0', 'map', 'marker_frame_2']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_3',
            arguments=['0.0', '2.0', '0.2', '-1.5708', '0.0', '0.0', 'map', 'marker_frame_3']
        ),

        # ArUco Relocalization Node
        Node(
            package='esp32_camera_streamer',
            executable='aruco_transformer',
            name='aruco_transformer',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}]
        ),

        # Robot Localization (EKF Filter)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[ekf_params_file, {'use_sim_time': use_sim_time}]
        ),

        # Nav2 Autonomous Navigation Stack
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_nav2_bringup, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'map': map_yaml_file,
                'params_file': nav2_params_file,
                'use_sim_time': use_sim_time,
                'autostart': 'true'
            }.items()
        ),

        # RViz Visualization
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': use_sim_time}]
        )
    ])
