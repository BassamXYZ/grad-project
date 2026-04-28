from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')

    teleop_keyboard = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}, {'stamped': True}, {'frame_id': 'chassis'}],
        remappings=[('/cmd_vel', '/cmd_vel_joy')]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use sim time if true'),
        teleop_keyboard,
    ])
