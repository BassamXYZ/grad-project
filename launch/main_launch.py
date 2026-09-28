import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue 

def generate_launch_description():

    pkg_grad_project = get_package_share_directory('grad-project')
    pkg_esp32_streamer = get_package_share_directory('esp32_camera_streamer')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_aruco = get_package_share_directory('ros2_aruco')

    xacro_file = os.path.join(pkg_grad_project, 'description', 'robot.urdf.xacro')
    ekf_params_file = os.path.join(pkg_grad_project, 'config', 'ekf.yaml')
    map_yaml_file = os.path.join(pkg_grad_project, 'maps', 'room_map.yaml')
    nav2_params_file = os.path.join(pkg_grad_project, 'config', 'nav2_params.yaml')
    twist_mux_params_file = os.path.join(pkg_grad_project, 'config', 'twist_mux.yaml')
    rviz_config_file = os.path.join(pkg_grad_project, 'config', 'default.rviz')
    aruco_params = os.path.join(pkg_aruco, 'config', 'aruco_parameters.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_description_raw = Command(['xacro ', xacro_file, ' sim_mode:=', use_sim_time])
    robot_description_param = ParameterValue(robot_description_raw, value_type=str)
    params = {'robot_description': robot_description_param, 'use_sim_time': use_sim_time}

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use sim time if true'
        ),
        
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[params]
        ),

        Node(
            package='twist_mux',
            executable='twist_mux',
            name='twist_mux',
            output='screen',
            parameters=[twist_mux_params_file],
            remappings=[
                ('/cmd_vel_out', '/cmd_vel')
            ]
        ),
        
        Node(
            package='esp32_camera_streamer',
            executable='phone_camera_publisher',
            name='esp32_camera_streamer',
            output='screen'
        ),

        Node(
            package='ros2_aruco',
            executable='aruco_node',
            parameters=[aruco_params]
        ),
            
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_1',
            arguments=['0.5', '0.5', '0.02', '2.2708', '0.0', '0.0', 'map', 'marker_frame_1']
        ),
        
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_0',
            arguments=['1.5', '0.5', '0.02', '-2.2708', '0.0', '0.0', 'map', 'marker_frame_0']
        ),
        
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_2',
            arguments=['1.5', '1.5', '0.02', '-0.7858', '0.0', '0.0', 'map', 'marker_frame_2']
        ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_marker_3',
            arguments=['0.5', '1.5', '0.02', '0.7858', '0.0', '0.0', 'map', 'marker_frame_3']
        ),
        
        Node(
            package='esp32_camera_streamer',
            executable='aruco_transformer',
            name='aruco_transformer',
            output='screen'
        ),

        # لا يوجد أي عقدة أخرى تنشر التحويل map -> odom (لا يوجد lidar لتشغيل amcl بشكل فعلي،
        # وaruco_transformer كان يحاول قراءة تحويل غير موجود بين marker_frame و odom).
        # لذلك تبقى شجرتا TF منفصلتين وnav2 يفشل بالخطأ:
        # "Could not find a connection between 'map' and 'base_link'".
        # بما أن ekf_filter_node يدمج قياسات aruco المطلقة (pose0) مباشرة داخل إطار odom،
        # فإن odom يصبح فعليًا مطابقًا لإحداثيات map، لذلك ربط الإطارين بتحويل ثابت (identity)
        # هو حل عملي وسريع لربط الشجرتين دون الحاجة لـ EKF ثانٍ.
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_map_to_odom',
            arguments=['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', 'map', 'odom']
        ),

        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[ekf_params_file]
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_nav2_bringup, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'map': map_yaml_file,
                'params_file': nav2_params_file,
                'use_sim_time': 'false',
                'autostart': 'true'
            }.items()
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file]
        )
    ])
