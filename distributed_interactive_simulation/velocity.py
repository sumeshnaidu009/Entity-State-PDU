#! /usr/bin/python

# Various coordinate system transform utilities. DIS uses 
# an Earth-Centered, Earth-Fixed coordinate system, with the
# origin at the center of the (WGS84) earth, positive x out
# at the equator and prime meridian, z out through the north
# pole, and y out at the equator and 90 deg east. We often want
# to convert those coordinates to latitude, longitude, and altitude
# on the WGS84 globe. This utility does that. (It's swiped from
# the net, specifically the stoqs project at MBARI)

__author__ = "mcgredo"
__date__ = "$Jun 25, 2015 10:23:43 AM$"

#!/usr/bin/env python
# See https://github.com/GAVLab/fhwa2_viz/blob/master/fhwa2_gui/src/util.py
"""
Container for general GPS functions and classes
Functions:
    deg2rad
    rad2deg
    euclideanDistance
    gpsWeekCheck
    keplerE
Classes:
    GPS - includes functions:
        lla2ecef
        ecef2lla
    WGS84 - constant parameters for GPS class
"""
#Import required packages
from math import sqrt, pi, sin, cos, tan, atan, atan2
from numpy import array, dot
#from numarray import array, dot, zeros, Float64

#def diag(l):
#    length = len(l)
#    a = zeros((length, length), Float64)
#    for index in range(length):
#        a[index, index] = l[index]
#    return a


def deg2rad(deg):
    """Converts degrees to radians"""
    return deg * pi / 180


def rad2deg(rad):
    """Converts radians to degrees"""
    return rad * 180 / pi


def isEven(num):
    """Boolean function returning true if num is even, false if not"""
    return num%2 == 0


def euclideanDistance(data, dataRef=None):
    """Calculates the Euclidian distance between the given data and zero.
    This works out to be equivalent to the distance between two points if their
    difference is given as the input"""
    total = 0
    for index in range(len(data)):
        if dataRef is None:
            total += data[index]**2
        else:
            total += (data[index] - dataRef[index])**2
    return sqrt(total)


def gpsWeekCheck(t):
    """Makes sure the time is in the interval [-302400 302400] seconds, which
    corresponds to number of seconds in the GPS week"""
    if t > 302400.:
        t = t - 604800.
    elif t < -302400.:
        t = t + 604800.
    return t


def keplerE(M_k, ecc, tolerance=1e-12):
    """Iteratively calculates E_k using Kepler's equation:
    E_k = M_k + ecc * sin(E_k)"""
    E_k = M_k
    E_0 = E_k + tolerance * 10.
    while abs(E_k - E_0) > tolerance:
        E_0 = E_k
        E_k = M_k + ecc * sin(E_k)
    return E_k

'''
def normalize(x,y,z):
    l=sqrt(x*x+y*y+z*z)
    if (l>1e-6):
        x*=1
        y*=1
        z*=1
'''

class WGS84:
    """General parameters defined by the WGS84 system"""
    #Semimajor axis length (m)
    a = 6378137.0
    #Semiminor axis length (m)
    b = 6356752.3142
    #Ellipsoid flatness (unitless)
    f = (a - b) / a
    #Eccentricity (unitless)
    e = sqrt(f * (2 - f))
    #Speed of light (m/s)
    c = 299792458.
    #Relativistic constant
    F = -4.442807633e-10
    #Earth's universal gravitational constant
    mu = 3.986005e14
    #Earth rotation rate (rad/s)
    omega_ie = 7.2921151467e-5

    def g0(self, L):
        """acceleration due to gravity at the elipsoid surface at latitude L"""
        return 9.7803267715 * (1 + 0.001931851353 * sin(L)**2) / \
                        sqrt(1 - 0.0066943800229 * sin(L)**2)



class GPS:
    """Working class for GPS module"""
    wgs84 = WGS84()
    fGPS = 1023
    fL1 = fGPS * 1.54e6
    fL2 = fGPS * 1.2e6

    def lla2ecef(self, lla):
        """Convert lat, lon, alt to Earth-centered, Earth-fixed coordinates.
        Input: lla - (lat, lon, alt) in (decimal degrees, decimal degees, m)
        Output: ecef - (x, y, z) in (m, m, m)
        """
        #Decompose the input
        lat = deg2rad(lla[0])
        lon = deg2rad(lla[1])
        alt = lla[2]
        #Calculate length of the normal to the ellipsoid
        N = self.wgs84.a / sqrt(1 - (self.wgs84.e * sin(lat))**2)
        #Calculate ecef coordinates
        x = (N + alt) * cos(lat) * cos(lon)
        y = (N + alt) * cos(lat) * sin(lon)
        z = (N * (1 - self.wgs84.e**2) + alt) * sin(lat)
        #Return the ecef coordinates
        return (x, y, z)
