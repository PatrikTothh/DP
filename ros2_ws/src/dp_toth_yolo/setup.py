from setuptools import setup
from glob import glob
import os

package_name = 'dp_toth_yolo'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],

    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),

        ('share/' + package_name,
         ['package.xml']),

        (os.path.join('share', package_name, 'launch'),
         glob('launch/*.launch.py')),

        (os.path.join('share', package_name, 'config'),
         glob('config/*.yaml')),
    ],

    install_requires=['setuptools'],
    zip_safe=True,

    maintainer='patrik',
    maintainer_email='DOPLN_EMAIL',
    description='ROS2 modul na detekciu objektov pomocou YOLO.',
    license='DOPLN_LICENCIU',

    tests_require=['pytest'],

    entry_points={
    'console_scripts': [
        'yolo_detector = dp_toth_yolo.yolo_detector:main',
        ],
    },
)