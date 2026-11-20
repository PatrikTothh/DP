#!/bin/bash

# Cesty k projektu
PROJECT_DIR="$HOME/DP"
MODEL_PATH="$PROJECT_DIR/models/traffic_signs_v1.pt"

# Kontrola modelu
if [ ! -f "$MODEL_PATH" ]; then
    echo "CHYBA: YOLO model neexistuje: $MODEL_PATH"
    exit 1
fi

# Kontrola terminalu
if ! command -v gnome-terminal >/dev/null 2>&1; then
    echo "CHYBA: gnome-terminal nie je nainstalovany."
    exit 1
fi

echo "Spustam JetRacer YOLO ROS2..."

# 1. Kamera notebooku
gnome-terminal --title="ROS2 - Kamera" -- bash -c '
    source /opt/ros/humble/setup.bash
    ros2 run v4l2_camera v4l2_camera_node
    exec bash
'

# 2. YOLO detekcna noda
gnome-terminal --title="ROS2 - YOLO Detector" -- bash -c "
    source /opt/ros/humble/setup.bash
    source '$PROJECT_DIR/.venv/bin/activate'
    source '$PROJECT_DIR/ros2_ws/install/setup.bash'

    ros2 run jetracer_yolo detector --ros-args \
        -p model_path:='$MODEL_PATH'

    exec bash
"

# 3. Vizualizacia
gnome-terminal --title="ROS2 - Visualization" -- bash -c '
    source /opt/ros/humble/setup.bash
    ros2 run rqt_image_view rqt_image_view
    exec bash
'

echo "Spustacie prikazy boli odoslane."