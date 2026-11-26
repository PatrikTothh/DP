import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    package_dir = get_package_share_directory(
        'dp_toth_capture'
    )

    config_file = os.path.join(
        package_dir,
        'config',
        'capture_params.yaml'
    )

    # Launch argumenty
    camera_device = LaunchConfiguration('camera_device')
    image_topic = LaunchConfiguration('image_topic')
    start_camera = LaunchConfiguration('start_camera')

    output_dir = LaunchConfiguration('output_dir')
    session_name = LaunchConfiguration('session_name')

    capture_interval = LaunchConfiguration('capture_interval')
    auto_capture = LaunchConfiguration('auto_capture')
    show_preview = LaunchConfiguration('show_preview')

    # --------------------------------------------------
    # Kamera
    # --------------------------------------------------

    camera_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='v4l2_camera',

        parameters=[{
            'video_device': camera_device
        }],

        remappings=[
            ('/image_raw', image_topic)
        ],

        condition=IfCondition(start_camera),
        output='screen'
    )

    # --------------------------------------------------
    # Image Capture
    # --------------------------------------------------

    capture_node = Node(
        package='dp_toth_capture',
        executable='image_capture',
        name='image_capture',

        parameters=[
            config_file,
            {
                'image_topic': ParameterValue(
                    image_topic,
                    value_type=str
                ),

                'output_dir': ParameterValue(
                    output_dir,
                    value_type=str
                ),

                'session_name': ParameterValue(
                    session_name,
                    value_type=str
                ),

                'capture_interval': ParameterValue(
                    capture_interval,
                    value_type=float
                ),

                'auto_capture': ParameterValue(
                    auto_capture,
                    value_type=bool
                ),

                'show_preview': ParameterValue(
                    show_preview,
                    value_type=bool
                )
            }
        ],

        output='screen',

        # Pri ukonceni image_capture ukoncime aj launch
        on_exit=Shutdown(
            reason='Image Capture bol ukonceny'
        )
    )

    return LaunchDescription([

        # Kamera
        DeclareLaunchArgument(
            'camera_device',
            default_value='/dev/video0'
        ),

        DeclareLaunchArgument(
            'image_topic',
            default_value='/image_raw'
        ),

        DeclareLaunchArgument(
            'start_camera',
            default_value='true'
        ),

        # Ukladanie
        DeclareLaunchArgument(
            'output_dir',
            default_value='~/DP/datasets/captured'
        ),

        DeclareLaunchArgument(
            'session_name',
            default_value='default'
        ),

        # Zachytavanie
        DeclareLaunchArgument(
            'capture_interval',
            default_value='0.5'
        ),

        DeclareLaunchArgument(
            'auto_capture',
            default_value='false'
        ),

        # GUI
        DeclareLaunchArgument(
            'show_preview',
            default_value='false'
        ),

        camera_node,
        capture_node

    ])