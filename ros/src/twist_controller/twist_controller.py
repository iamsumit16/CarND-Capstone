import rospy
from pid import PID
from lowpass import LowPassFilter
from yaw_controller import YawController


GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self, vehicle_mass, fuel_capacity, brake_deadband, decel_limit,
        accel_limit, wheel_radius, wheel_base, steer_ratio, max_lat_accel, max_steer_angle):

        # Create an object with class YawController
        self.yaw_controller = YawController(wheel_base, steer_ratio, 0.1, max_lat_accel, max_steer_angle)

        # Define PID tuning parameters for the throttle controller
        kp = 0.3   #5, 0.3
        ki = 0.1 #0.5, 0.1
        kd = 0. # 0.5, 0.
        mn = 0.  # Minimum throttle value
        mx = 0.2 # Maximum throttle value
        

        tau = 0.5 # 1/(2pi*tau) = cutoff frequency
        ts = 0.02 # Sample time
        
        self.vel_lpf = LowPassFilter(tau, ts)
        self.steer_lpf = LowPassFilter(tau, ts) 
        self.vel_lpf = LowPassFilter(tau, ts)
        self.t_lpf = LowPassFilter(tau, ts)
        
        self.vehicle_mass = vehicle_mass
        self.fuel_capacity = fuel_capacity
        self.brake_deadband = brake_deadband
        self.decel_limit = decel_limit
        self.accel_limit = accel_limit
        self.wheel_radius = wheel_radius
     
        self.last_time = rospy.get_time()
        self.throttle_controller = PID(kp, ki, kd, -5, 1)
        
    def control(self, current_vel, dbw_enabled, linear_vel, angular_vel):
        # The function uses the YawController class and PID class to calculate the throttle, steering inputs and applies the brake based on throttle, velocity.
        # Return throttle, brake, steer
        if not dbw_enabled:
            self.throttle_controller.reset()
            return 0., 0., 0.
        
        current_vel = self.vel_lpf.filt(current_vel)
        vel_error = linear_vel - current_vel
       
        
        steering = self.yaw_controller.get_steering(linear_vel, angular_vel, current_vel)
        steering = self.steer_lpf.filt(steering)
        
        
        self.last_vel = current_vel
        current_time = rospy.get_time()
        sample_time = current_time - self.last_time
        self.last_time = current_time

        acc = self.throttle_controller.step(vel_error, sample_time)
        acc = self.t_lpf.filt(acc)
        
        
        brake = 0.0
        
        if linear_vel == 0.0:                # and current_vel < 0.1:
            throttle = 0.0
            brake = 700                      #N-m - to hold the car in place if we stopped at a light. 
            self.throttle_controller.reset()
            
        else:                                # and vel_error < 0:
            throttle = acc
            if acc <= 0.0:
                throttle = 0
                decel = -acc
                if decel < self.brake_deadband: 
                    decel = 0
                brake = abs(decel)* (self.vehicle_mass + self.fuel_capacity*GAS_DENSITY) * self.wheel_radius 
            

        return throttle, brake, steering
