#!/usr/bin/env python

import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
import tf

import math
import tf

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number
TIMEOUT_VALUE = 10.0

class WaypointUpdater(object):
    def __init__(self):
        rospy.loginfo('WaypointUpdater::__init__ - Start')
        rospy.init_node('waypoint_updater')
        rospy.loginfo('WaypointUpdater::__init__ - subscribing to /current_pose')
        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.loginfo('WaypointUpdater::__init__ - subscribing to /base_waypoints')
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.loginfo('WaypointUpdater::__init__ - subscribing to /traffic_waypoint')
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)
        # commenting the two below for the time being until clarification about whether
        # is needed or not
        #rospy.loginfo('WaypointUpdater::__init__ - subscribing to /obstacle_waypoint')
        #rospy.Subscriber('/obstacle_waypoint', , self.obstacle_cb)

        rospy.loginfo('WaypointUpdater::__init__ - publishing to /final_waypoints')
        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.tf_listener = tf.TransformListener()

        self.default_velocity = rospy.get_param('~velocity', 0)

        rospy.loginfo('WaypointUpdater::__init__ - End (just before executing spin())')
        rospy.spin()

    def pose_cb(self, msg):
        rospy.loginfo('WaypointUpdater::pose_cb - Start')
        rospy.loginfo('WaypointUpdater::pose_cb - Pose rcvd X:%s, Y:%s, Z:%s, rX:%s, rY:%s, rZ:%s, rW:%s for frame %s', msg.pose.position.x, msg.pose.position.y, msg.pose.position.z, msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z, msg.pose.orientation.w, msg.header.frame_id)
        rospy.loginfo('WaypointUpdater::pose_cb - End')

    def waypoints_cb(self, waypoints):
        # let's log some information about the received list of waypoints
        rospy.loginfo('WaypointUpdater::waypoints_cb - Start')
        rospy.loginfo('WaypointUpdater::waypoints_cb - Rcvd list of %s waypoints on frame %s', len(waypoints.waypoints), waypoints.header.frame_id)

        first_wpt_index = -1
        min_wpt_distance_squared = float('inf')
        # iterate through the complete set of waypoints received
        for index, waypoint in enumerate(waypoints.waypoints):
            try:
                # I need to make sure that the header part of each PoseStamped element in the waypoints list is correctly
                # initialized... for some reason they are not
                waypoint.pose.header.frame_id = waypoints.header.frame_id
                self.tf_listener.waitForTransform("/base_link", "/world", rospy.Time(0), rospy.Duration(TIMEOUT_VALUE))
                transformed_waypoint = self.tf_listener.transformPose("/base_link", waypoint.pose)
                # all waypoints in front of the car should have positive X coordinate in car coordinate frame
                # let's find the one with the smallest positive X coordinate and store it's index in the waypoint list
                current_wpt_distance_squared = transformed_waypoint.pose.position.x**2 + transformed_waypoint.pose.position.y**2
                if transformed_waypoint.pose.position.x > 0.0 and current_wpt_distance_squared < min_wpt_distance_squared:
                    min_wpt_distance_squared = current_wpt_distance_squared
                    first_wpt_index = index

            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                rospy.logerr('WaypointUpdater::waypoints_cb - could not get coordinate frame transform!!!')

        if first_wpt_index == -1:
            rospy.logwarn('WaypointUpdater::waypoints_cb - No waypoints ahead of ego were found... seems that the car went off course')
        else:
            rospy.loginfo('WaypointUpdater::waypoints_cb - Found the index %s to be the next waypoint', first_wpt_index)
            # now let's only leave these points in the list
            waypoints.waypoints = waypoints.waypoints[first_wpt_index:first_wpt_index + LOOKAHEAD_WPS]
            rospy.loginfo('WaypointUpdater::waypoints_cb - Left only %s waypoints in the list', len(waypoints.waypoints))
            # then, for the first stage of the implementation, set a dummy velocity to all these waypoints
            # so that the car is intructed to drive around the track
            rospy.loginfo('WaypointUpdater::waypoints_cb - Setting waypoints twist.linear.x = %s', self.default_velocity)
            for waypoint in waypoints.waypoints:
                waypoint.twist.twist.linear.x = self.default_velocity

        # finally, publish waypoints as modified on /final_waypoints topic
        rospy.loginfo('WaypointUpdater::waypoints_cb - publishing new waypoint list on /final_waypoints')
        self.final_waypoints_pub.publish(waypoints)
        rospy.loginfo('WaypointUpdater::waypoints_cb - End')

    def traffic_cb(self, traffic_waypoint):
        # TODO: Callback for /traffic_waypoint message. Implement
        pass

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
