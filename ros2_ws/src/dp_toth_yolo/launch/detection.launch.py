import os

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # Cesta ku konfiguracii
    package_dir = get_package_share_directory('dp_toth_yolo')

    config_file = os.path.join(
        package_dir,
        'config',
        'yolo_params.yaml'
    )

    return LaunchDescription([

        # Kamera notebooku
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='v4l2_camera',
            output='screen'
        ),

        # YOLO detekcna noda
        Node(
            package='dp_toth_yolo',
            executable='yolo_detector',
            name='yolo_detector',
            parameters=[config_file],
            output='screen'
        ),

        # Vizualizacia
        Node(
            package='rqt_image_view',
            executable='rqt_image_view',
            name='rqt_image_view',
            output='screen'
        )
    ])