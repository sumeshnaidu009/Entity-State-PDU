#! /usr/bin/python

import socket
import time
import sys
import pyModeS as pms
import numpy as np
import csv
import os
import pandas as pd
from pandas import DataFrame

sys.path.append("../dis_io")
sys.path.append("../distributed_interactive_simulation")

from DataInputStream import DataInputStream
from DataOutputStream import DataOutputStream

from dis7 import EntityStatePdu
from io import BytesIO
from RangeCoordinates import GPS

from pyModeS.decoder import commb, common, bds
from pyModeS.decoder import uncertainty
from pyModeS.decoder import adsb
from pyModeS.decoder.bds.bds05 import airborne_position, airborne_position_with_ref, altitude
from pyModeS.decoder.bds.bds06 import surface_position, surface_position_with_ref, surface_velocity
from pyModeS.decoder.bds.bds08 import category, callsign
from pyModeS.decoder.bds.bds09 import airborne_velocity, altitude_diff

UDP_PORT = 3000
DESTINATION_ADDRESS = "192.168.2.255"

udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

def entity_type():
    pdu = EntityStatePdu()
                                           
    pdu.exerciseID = 2
    ts = int(time.time())
    pdu.timestamp = ts
    pdu.length = 144
                                            
    pdu.entityID.siteID = 1
    pdu.entityID.applicationID = 1000
    pdu.forceId = 1
    pdu.entityID.entityID = 1
    position_data = { '471F4A' : [] }
    velocity_data = { 1 : [] }
    track = input('PLease enter the ICAO of available aircraft with in the radius of 330Km...')
    while True:
            
        opn = open('/home/pi/pyModeS-master/tests/data/d.csv','rt')
        for i, r in enumerate(csv.reader(opn)):
            if r:                
                m = r[0]
                if r[0] == '' :
                    time.sleep(1000)
                elif len(m) == 30 :
                    hexstr = m[1:29]
                    df = pms.df(hexstr)
                    icao = adsb.icao(hexstr)                    
                    tc = adsb.typecode(hexstr)
                    msg_even = None
                    msg_odd = None
                    lat_ref = 47.6676454
                    lon_ref = 9.3847333

                    if icao == track :
                        f = csv.reader(open('/home/pi/pyModeS-master/tests/data/icao-model.csv',"rt"))
                                            
                        for row in f:
                            if icao == row[0]:
                                                                    
                                x = row
                                model = x[1]
                                           
                                g = csv.reader(open('/home/pi/pyModeS-master/tests/data/model-entity_id.csv',"rt"))
                                for row in g:
                                    if model == row[0]:
                                        entityID = row[1]
                                        entityKind = row[2]                                    
                                        domain = row[3]                                    
                                        country = row[4]                                    
                                        category = row[5]                                    
                                        subcategory = row[6]                                    
                                        specific = row[7]                                    
                                        extra = row[8]
                                                                                                
                                        pdu.entityType.entityKind = int(entityKind)                        
                                        pdu.entityType.domain = int(domain)                                  
                                        pdu.entityType.country = int(country)                                        
                                        pdu.entityType.category = int(category)
                                        pdu.entityType.subcategory = int(subcategory)
                                        pdu.entityType.specific = int(specific)
                                        pdu.entityType.extra = int(extra)

                                        pdu.alternativeEntityType.entityKind = int(entityKind)
                                        pdu.alternativeEntityType.domain = int(domain)
                                        pdu.alternativeEntityType.country = int(country)
                                        pdu.alternativeEntityType.category = int(category)
                                        pdu.alternativeEntityType.subcategory = int(subcategory)
                                        pdu.alternativeEntityType.specific = int(specific)
                                        pdu.alternativeEntityType.extra = int(extra)

                                        print (hexstr,icao)
                                        if df==17 or df==18 :
                                                
                                            if 1 <= tc <= 4:
                                                category = adsb.category(hexstr)                                                                
                                                                                
                                            elif (5<=tc<=8) :
                                                ts = int(time.time())
                                                k = icao
                                                if hexstr in position_data[k]:
                                                    print('that is the last position received........')
                                                elif k in position_data:
                                                    position_data[k].append(hexstr)
                                                    position_data[k].append(ts)
                                                    obj = position_data[k]
                                                    l2 = obj[len(obj)-2]
                                                    l1 = obj[len(obj)-4]
                                                    t2 = obj[len(obj)-1]
                                                    t1 = obj[len(obj)-3]
                                                    eo2 = adsb.oe_flag(l2)
                                                    eo1 = adsb.oe_flag(l1)
                                                    
                                                    if eo2 == 0 and eo1 == 1:                                
                                                        msg_even = l2
                                                        t_even = t2                           
                                                        msg_odd = l1
                                                        t_odd = t1
                                                                                                                
                                                        position = pms.adsb.position(msg_even, msg_odd, t_even, t_odd, lat_ref, lon_ref)
                                                        lat = position[0]
                                                        lon = position[1]
                                                        altitude = pms.adsb.altitude(hexstr)
                                                        alt = altitude*0.305                                        # converting feets to meters
                                                        print('input position',lat,lon,alt)

                                                        gps = GPS()           
                                                        montereyLocation = gps.lla2ecef((lat,lon,alt))
                                                        pdu.entityLocation.x = montereyLocation[0]
                                                        pdu.entityLocation.y = montereyLocation[1]
                                                        pdu.entityLocation.z = montereyLocation[2]
                                                        fid = pdu.entityID.entityID
                                                        p = [pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z] # x,y,z are in meters
                                                        print('ecef',p)

                                                        if fid not in velocity_data:
                                                            velocity_data[fid] = [[0.0,0.0,0.0,ts],p]
                                                            p.append(ts)
                                                            
                                                        else:        
                                                            velocity_data[fid].append(p)
                                                            p.append(ts)
                                                            fobject = velocity_data[fid]
                                                            list2 = fobject[len(fobject)-1]
                                                            list1 = fobject[len(fobject)-2]        
                                                            result = []
                                                            if len(list2) == len(list1):
                                                                for i,j in zip(list2,list1):
                                                                    diff = i-j
                                                                    result.append(diff)
                                                                if result[3] != 0:
                                                                    v = (result[0]/result[3],result[1]/result[3],result[2]/result[3])
                                                                    pdu.entityLinearVelocity.x = v[0]
                                                                    pdu.entityLinearVelocity.y = v[1]
                                                                    pdu.entityLinearVelocity.z = v[2]
                                                                    print(pdu.entityLinearVelocity.x,pdu.entityLinearVelocity.y,pdu.entityLinearVelocity.z)
                                                                #print(d)
                                                                #print(fid,result)
                                                            else:
                                                                print("list lengths are not same")
                                                    elif eo2 == 1 and eo1 == 0:
                                                        msg_even = l1
                                                        t_even = t1
                                                        msg_odd = l2
                                                        t_odd = t2

                                                        position = pms.adsb.position(msg_even, msg_odd, t_even, t_odd, lat_ref, lon_ref)
                                                        lat = position[0]
                                                        lon = position[1]
                                                        altitude = pms.adsb.altitude(hexstr)
                                                        alt = altitude*0.305                             # converting feets to meters
                                                        print('input position',lat,lon,alt)
                                                        
                                                        gps = GPS()           
                                                        montereyLocation = gps.lla2ecef((lat,lon,alt))
                                                        pdu.entityLocation.x = montereyLocation[0]
                                                        pdu.entityLocation.y = montereyLocation[1]
                                                        pdu.entityLocation.z = montereyLocation[2]
                                                        fid = pdu.entityID.entityID
                                                        p = [pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z] # x,y,z are in meters
                                                        print('ecef',p)
                                                        
                                                        if fid not in velocity_data:
                                                            velocity_data[fid] = [[0.0,0.0,0.0,ts],p]
                                                            p.append(ts)
                                                            
                                                        else:        
                                                            velocity_data[fid].append(p)
                                                            p.append(ts)
                                                            fobject = velocity_data[fid]
                                                            list2 = fobject[len(fobject)-1]
                                                            list1 = fobject[len(fobject)-2]        
                                                            result = []
                                                            if len(list2) == len(list1):
                                                                for i,j in zip(list2,list1):
                                                                    diff = i-j
                                                                    result.append(diff)
                                                                if result[3] != 0:
                                                                    v = (result[0]/result[3],result[1]/result[3],result[2]/result[3])
                                                                    pdu.entityLinearVelocity.x = v[0]
                                                                    pdu.entityLinearVelocity.y = v[1]
                                                                    pdu.entityLinearVelocity.z = v[2]
                                                                    print(pdu.entityLinearVelocity.x,pdu.entityLinearVelocity.y,pdu.entityLinearVelocity.z)
                                                                #print(d)
                                                                #print(fid,result)
                                                            else:
                                                                print("list lengths are not same")
                                                                                                                                    
                                                        otherLocation = (montereyLocation[0], montereyLocation[1], montereyLocation[2] + 1)
                                                        ned = gps.ecef2ned(montereyLocation, otherLocation)                                              
                                                        
                                            elif (9<=tc<=18) :
                                                ts = int(time.time())
                                                k = icao
                                                if hexstr in position_data[k]:
                                                    print('that is the last position received.........')
                                                elif k in position_data:
                                                    position_data[k].append(hexstr)
                                                    position_data[k].append(ts)
                                                    obj = position_data[k]
                                                    l2 = obj[len(obj)-2]
                                                    l1 = obj[len(obj)-4]
                                                    t2 = obj[len(obj)-1]
                                                    t1 = obj[len(obj)-3]
                                                    eo2 = adsb.oe_flag(l2)
                                                    eo1 = adsb.oe_flag(l1)
                                                    
                                                    if eo2 == 0 and eo1 == 1:                                
                                                        msg_even = l2
                                                        t_even = t2                           
                                                        msg_odd = l1
                                                        t_odd = t1
                                                                                                                
                                                        position = pms.adsb.position(msg_even, msg_odd, t_even, t_odd, lat_ref, lon_ref)
                                                        lat = position[0]
                                                        lon = position[1]
                                                        altitude = pms.adsb.altitude(hexstr)
                                                        alt = altitude*0.305                                        # converting feets to meters
                                                        print('input position',lat,lon,alt)

                                                        gps = GPS()           
                                                        montereyLocation = gps.lla2ecef((lat,lon,alt))
                                                        pdu.entityLocation.x = montereyLocation[0]
                                                        pdu.entityLocation.y = montereyLocation[1]
                                                        pdu.entityLocation.z = montereyLocation[2]
                                                        fid = pdu.entityID.entityID
                                                        p = [pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z] # x,y,z are in meters
                                                        print(p)

                                                        if fid not in velocity_data:
                                                            velocity_data[fid] = [[0.0,0.0,0.0,ts],p]
                                                            p.append(ts)
                                                            
                                                        else:        
                                                            velocity_data[fid].append(p)
                                                            p.append(ts)
                                                            fobject = velocity_data[fid]
                                                            list2 = fobject[len(fobject)-1]
                                                            list1 = fobject[len(fobject)-2]        
                                                            result = []
                                                            if len(list2) == len(list1):
                                                                for i,j in zip(list2,list1):
                                                                    diff = i-j
                                                                    result.append(diff)
                                                                if result[3] != 0:
                                                                    v = (result[0]/result[3],result[1]/result[3],result[2]/result[3])
                                                                    pdu.entityLinearVelocity.x = v[0]
                                                                    pdu.entityLinearVelocity.y = v[1]
                                                                    pdu.entityLinearVelocity.z = v[2]
                                                                    print(pdu.entityLinearVelocity.x,pdu.entityLinearVelocity.y,pdu.entityLinearVelocity.z)
                                                                #print(d)
                                                                #print(fid,result)
                                                            else:
                                                                print("list lengths are not same")
                                                    elif eo2 == 1 and eo1 == 0:
                                                        msg_even = l1
                                                        t_even = t1
                                                        msg_odd = l2
                                                        t_odd = t2

                                                        position = pms.adsb.position(msg_even, msg_odd, t_even, t_odd, lat_ref, lon_ref)
                                                        lat = position[0]
                                                        lon = position[1]
                                                        altitude = pms.adsb.altitude(hexstr)
                                                        alt = altitude*0.305                        # converting feets to meters
                                                        print('input position',lat,lon,alt)
                                                        
                                                        gps = GPS()           
                                                        montereyLocation = gps.lla2ecef((lat,lon,alt))
                                                        pdu.entityLocation.x = montereyLocation[0]
                                                        pdu.entityLocation.y = montereyLocation[1]
                                                        pdu.entityLocation.z = montereyLocation[2]
                                                        fid = pdu.entityID.entityID
                                                        p = [pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z] # x,y,z are in meters
                                                        print('ecef',p)
                                                        
                                                        if fid not in velocity_data:
                                                            velocity_data[fid] = [[0.0,0.0,0.0,ts],p]
                                                            p.append(ts)
                                                            
                                                        else:        
                                                            velocity_data[fid].append(p)
                                                            p.append(ts)
                                                            fobject = velocity_data[fid]
                                                            list2 = fobject[len(fobject)-1]
                                                            list1 = fobject[len(fobject)-2]        
                                                            result = []
                                                            if len(list2) == len(list1):
                                                                for i,j in zip(list2,list1):
                                                                    diff = i-j
                                                                    result.append(diff)
                                                                if result[3] != 0:
                                                                    v = (result[0]/result[3],result[1]/result[3],result[2]/result[3])
                                                                    pdu.entityLinearVelocity.x = v[0]
                                                                    pdu.entityLinearVelocity.y = v[1]
                                                                    pdu.entityLinearVelocity.z = v[2]
                                                                    print(pdu.entityLinearVelocity.x,pdu.entityLinearVelocity.y,pdu.entityLinearVelocity.z)
                                                                #print(d)
                                                                #print(fid,result)
                                                            else:
                                                                print("list lengths are not same")
                                                                                                                                    
                                                        otherLocation = (montereyLocation[0], montereyLocation[1], montereyLocation[2] + 1)
                                                        ned = gps.ecef2ned(montereyLocation, otherLocation)

                                            elif tc==19 :
                                                velocity = pms.adsb.velocity(hexstr)               # Handles both surface & airborne messages
                                                speed_heading = pms.adsb.speed_heading(hexstr)     # Handles both surface & airborne messages
                                                airborne_velocity = pms.adsb.airborne_velocity(hexstr)
                                                                
                                                
                                        elif df==16 or df==20 :
                                            altcode = common.altcode(hexstr)
                                                            
                                                                       
                                        elif df==21 :
                                            idcode = common.idcode(hexstr)
                                               
                                        #print('done')             

                                        pdu.marking.characterSet = 1
                                        marking = [0,0,0,0,0,0,0]
                                        m = [ord(c) for c in model]
                                                    
                                        pdu.marking.characters = m+marking #[101,49,57,48,0,0,0,0,0,0,0]
                                        #print (pdu.marking.characters)
                                        '''
                                        #Orientation
                                        pi = 3.1415926536
                                        
                                        roll = pms.decoder.bds.bds50.roll50(hexstr)
                                        if roll != None:
                                            roll = pms.decoder.bds.bds50.roll50(hexstr)
                                            pdu.entityOrientation.phi= roll * (pi/180)   #in radians
                                            
                                        trk = pms.decoder.bds.bds50.trk50(hexstr)
                                        if trk != None:        
                                            trk = pms.decoder.bds.bds50.trk50(hexstr)
                                            pdu.entityOrientation.theta = trk * (pi/180) #in radians 
                                            
                                        hdg = pms.decoder.bds.bds60.hdg60(hexstr)
                                        if hdg != None:
                                            hdg = pms.decoder.bds.bds60.hdg60(hexstr)                                       
                                            pdu.entityOrientation.psi = hdg * (pi/180)   #in radians    '''                             
                                                                                                                    
                                            
                                        pdu.variableParameters = []
                                        pdu.entityAppearance = 0
                                        
                                        pdu.deadReckoningParameters.deadReckoningAlgorithm = 3
                                        pdu.deadReckoningParameters.parameters =  [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                        pdu.deadReckoningParameters.entityLinearAcceleration.x = 0
                                        pdu.deadReckoningParameters.entityLinearAcceleration.y = 0
                                        pdu.deadReckoningParameters.entityLinearAcceleration.z = 0
                                        pdu.deadReckoningParameters.entityAngularVelocity.x = 0
                                        pdu.deadReckoningParameters.entityAngularVelocity.y = 0
                                        pdu.deadReckoningParameters.entityAngularVelocity.z = 0
                                            
                                        #capability = pms.decoder.bds.bds17.cap17(hexstr)
                                        pdu.capabilities = 0#capability
                                                                                                            
                                        memoryStream = BytesIO()
                                        outputStream = DataOutputStream(memoryStream)
                                        pdu.serialize(outputStream)
                                        data = memoryStream.getvalue()
                                        pdu.length = len(data)
                                        #print ("data length is ", )
                                                    #print "pdu protocol version is ", pdu.protocolVersion
                                        memoryStream = BytesIO()
                                        outputStream = DataOutputStream(memoryStream)
                                        pdu.serialize(outputStream)
                                        data1 = memoryStream.getvalue()                 
                                        udpSocket.sendto(data1, (DESTINATION_ADDRESS, UDP_PORT))
                                                        
                                        #time.sleep(1)
                                        print ("message sent")
                        

if __name__ == "__main__":
    try:
        entity_type()
    except KeyboardInterrupt:
        print('Forced reset')

