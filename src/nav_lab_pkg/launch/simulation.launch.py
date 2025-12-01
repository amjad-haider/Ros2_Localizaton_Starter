import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    # 1. Get Package Paths
    pkg_nav_lab_pkg = get_package_share_directory('nav_lab_pkg')
    

    # 2. Define Launch Arguments

    # Argument to select the world file (Default is home.sdf)
    world_arg = DeclareLaunchArgument(
        'world', default_value='Austin_world.sdf',
        description='Name of the Gazebo world file (must be in /worlds folder)'
    )

    # Arguments for Spawning Position (Crucial for Localization challenges)
    x_arg = DeclareLaunchArgument('x', default_value='0.0', description='x coordinate')
    y_arg = DeclareLaunchArgument('y', default_value='0.0', description='y coordinate')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0', description='yaw angle')

    sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='True',
        description='Flag to enable use_sim_time'
    )

    model_arg = DeclareLaunchArgument(
        'model', default_value='ego_racer.urdf',
        description='Name of the URDF description to load'
    )

    # 3. Process Paths
    urdf_file_path = PathJoinSubstitution([
        pkg_nav_lab_pkg, "urdf", LaunchConfiguration('model')
    ])

    gz_bridge_params_path = os.path.join(
        pkg_nav_lab_pkg, 'config', 'gz_bridge.yaml'
    )
    # Define Path to RViz Config File
    rviz_config_file = PathJoinSubstitution([
        pkg_nav_lab_pkg, 
        'rviz', 
        'visualization.rviz'
    ])

    # 4. Include the World Launch (Gazebo)
    world_path = PathJoinSubstitution([
        get_package_share_directory('nav_lab_pkg'), # Your package name
        'worlds', 
        LaunchConfiguration('world')
    ])

    world_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': ['-r ', world_path]
        }.items()
    )


    # 5. Launch Nodes
    # RViz Node with Custom Configuration
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file], 
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # Spawn the Robot in Gazebo at specific X, Y, Yaw
    spawn_urdf_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name", "ego_racer",
            "-topic", "robot_description",
            "-x", LaunchConfiguration('x'), 
            "-y", LaunchConfiguration('y'), 
            "-z", "0.2", # Slight lift to prevent clipping floor
            "-Y", LaunchConfiguration('yaw')
        ],
        output="screen",
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # Robot State Publisher (Required for TF/Localization)
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'robot_description': Command(['xacro', ' ', urdf_file_path]),
             'use_sim_time': LaunchConfiguration('use_sim_time')},
        ],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static')
        ]
    )

    # ---------------------------------------------------------
    # BRIDGE NODES (Necessary for Sensor Data to reach ROS)
    # ---------------------------------------------------------

    # Bridge Cmd_vel and Odom
    gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            '--ros-args', '-p',
            f'config_file:={gz_bridge_params_path}'
        ],
        output="screen",
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # Bridge Camera
    gz_image_bridge_node = Node(
        package="ros_gz_image",
        executable="image_bridge",
        arguments=["/camera/image"],
        output="screen",
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time'),
             'camera.image.compressed.jpeg_quality': 75},
        ],
    )

    # Relay Camera Info
    relay_camera_info_node = Node(
        package='topic_tools',
        executable='relay',
        name='relay_camera_info',
        output='screen',
        arguments=['camera/camera_info', 'camera/image/camera_info'],
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )



    ld = LaunchDescription()

    ld.add_action(world_arg)
    ld.add_action(x_arg)
    ld.add_action(y_arg)
    ld.add_action(yaw_arg)
    ld.add_action(sim_time_arg)
    ld.add_action(model_arg)
    
    ld.add_action(world_launch)
    ld.add_action(rviz_node)
    ld.add_action(spawn_urdf_node)
    ld.add_action(robot_state_publisher_node)
    ld.add_action(gz_bridge_node)
    ld.add_action(gz_image_bridge_node)
    ld.add_action(relay_camera_info_node)

    return ld