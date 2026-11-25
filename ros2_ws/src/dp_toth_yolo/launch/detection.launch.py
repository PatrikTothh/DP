import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # Konfiguracny subor
    package_dir = get_package_share_directory('dp_toth_yolo')

    config_file = os.path.join(
        package_dir,
        'config',
        'yolo_params.yaml'
    )

    # Predvolena cesta k modelu
    default_model = os.path.join(
        os.path.expanduser('~'),
        'DP',
        'models',
        'traffic_signs_v1.pt'
    )

    # Argumenty
    camera_device = LaunchConfiguration('camera_device')
    image_topic = LaunchConfiguration('image_topic')
    start_camera = LaunchConfiguration('start_camera')
    show_image = LaunchConfiguration('show_image')
    model_path = LaunchConfiguration('model_path')

    return LaunchDescription([

        # Argumenty spustenia
        DeclareLaunchArgument(
            'camera_device',
            default_value='/dev/video0',
            description='Cesta k V4L2 kamere'
        ),

        DeclareLaunchArgument(
            'image_topic',
            default_value='/image_raw',
            description='Vstupny ROS2 obrazovy topic'
        ),

        DeclareLaunchArgument(
            'start_camera',
            default_value='true',
            description='Spustit V4L2 kameru'
        ),

        DeclareLaunchArgument(
            'show_image',
            default_value='true',
            description='Spustit rqt_image_view'
        ),

        DeclareLaunchArgument(
            'model_path',
            default_value=default_model,
            description='Cesta k YOLO modelu'
        ),

        # Kamera notebooku / USB kamera
        Node(
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
        ),

        # YOLO detekcna noda
        Node(
            package='dp_toth_yolo',
            executable='yolo_detector',
            name='yolo_detector',
            parameters=[
                config_file,
                {
                    'image_topic': image_topic,
                    'model_path': model_path
                }
            ],
            output='screen'
        ),

        # Vizualizacia
        Node(
            package='rqt_image_view',
            executable='rqt_image_view',
            name='rqt_image_view',
            condition=IfCondition(show_image),
            output='screen'
        )
    ])