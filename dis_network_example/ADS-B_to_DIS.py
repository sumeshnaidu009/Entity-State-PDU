import socket
import time
import sys
import pyModeS as pms
import numpy as np
import csv
import serial
import os

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


def get_model_from_icao(icao):
    '''Knowing the model of aircraft from the ICAO'''
    f = csv.reader(open('/home/pi/pyModeS-master/tests/data/icao-model.csv',"rt"))
                                    
    for row in f:
        
        if icao == row[0]:                                        
            x = row
            model = x[1]
            '''Marking entity by it's model'''
            pdu.marking.characterSet = 1
            marking = [0,0,0,0,0,0,0]
            m = [ord(c) for c in model]
                                            
            pdu.marking.characters = m+marking #[101,49,57,48,0,0,0,0,0,0,0]
            print(model,icao)
            return model
    else:
        print('new icao',icao)
        new_icao(icao)
        model = False
        return model
    
def new_icao(icao):
    with open('/home/pi/open-dis-python-master/src/main/python/dis_network_example/new_icao.csv', 'r+') as file:
        csv_file = csv.writer(file)
        for row in file:
            if icao in row:
                break
        else:
            csv_file.writerow([icao])
            
def get_entity_type_from_model(mo):
    '''Knowing entity type from model of aircraft'''       
    g = csv.reader(open('/home/pi/pyModeS-master/tests/data/model-entity_id.csv',"rt"))
    for row in g:
        if mo == row[0]:
            #entityID = row[1]
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


def get_ecef_position(hexstr,icao,df,tc):
    '''ADS-B messages are in downlink format 17 and 18.'''
    
            
    ts = int(time.time())  
    '''Creating a dictionary of position_data with key as ICAO and its values as a list of message received along with time.'''
    if icao not in position_data:
        position_data[icao] = [hexstr,ts]
        #print(position_data)
    else:
        position_data[icao].append(hexstr)
        position_data[icao].append(ts)
        print('got position msg')    
        obj = position_data[icao]
        '''l2 and l1 are the last and last second messages of the ICAO. t2 and t1 are the time stamps of the messages.'''
        l2 = obj[len(obj)-2]
        l1 = obj[len(obj)-4]
        t2 = obj[len(obj)-1]
        t1 = obj[len(obj)-3]
        '''Identifying even and odd messages, in order to calculate position.'''
        eo2 = adsb.oe_flag(l2)
        eo1 = adsb.oe_flag(l1)
                                                            
        if eo2 == 0 and eo1 == 1:
            print('type1 position')
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
            '''Calculating ecef co-ordinates from latitude,longitude and altitude.'''
            gps = GPS()           
            montereyLocation = gps.lla2ecef((lat,lon,alt))
            pdu.entityLocation.x = montereyLocation[0]
            pdu.entityLocation.y = montereyLocation[1]
            pdu.entityLocation.z = montereyLocation[2]
            #fid = pdu.entityID.entityID
            p = [pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z] # x,y,z are in meters
            '''Creating a dictionary of position_result with key as ICAO and its values as a list of ecef co-ordinates.'''
            if icao not in position_result:
                position_result[icao] =[p]
            else:
                position_result[icao].append(p)
            print('ecef',p)
            return (p)
                                
        elif eo2 == 1 and eo1 == 0:
            print('type2 position')
            msg_even = l1
            t_even = t1
            msg_odd = l2
            t_odd = t2

            position = pms.adsb.position(msg_even, msg_odd, t_even, t_odd, lat_ref, lon_ref)
            lat = position[0]
            lon = position[1]
            altitude = pms.adsb.altitude(hexstr)
            alt = altitude*0.305 # converting feets to meters
            print('input position',lat,lon,alt)
            '''Calculating ecef co-ordinates from latitude,longitude and altitude.'''
            gps = GPS()           
            montereyLocation = gps.lla2ecef((lat,lon,alt))
            pdu.entityLocation.x = montereyLocation[0]
            pdu.entityLocation.y = montereyLocation[1]
            pdu.entityLocation.z = montereyLocation[2]
            #fid = pdu.entityID.entityID
            p = [pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z] # x,y,z are in meters
            '''Creating a dictionary of position_result with key as ICAO and its values as a list of ecef co-ordinates.'''
            if icao not in position_result:
                position_result[icao] =[p]
            else:
                position_result[icao].append(p)
            print('ecef',p)
            return (p)
    

def aircraft_velocity(po):

    ts = int(time.time())
    '''Creating a dictionary of velocity_data with key as entity ID and its values as a list of ecef co-ordinates along with time.'''
    if icao not in velocity_data:
        velocity_data[icao] = [[0.0,0.0,0.0,ts],po]
        po.append(ts)
        
    else:
        velocity_data[icao].append(po)
        po.append(ts)
        fobject = velocity_data[icao]
        '''list2 and list1 are the last and last second ecef co-ordinates of the perticular entity.'''
        '''The differtence between these lists and dividing them with the difference between the time stamps  of those messages received gives the velocity.'''
        list2 = fobject[len(fobject)-1]
        list1 = fobject[len(fobject)-2]
        result = []
        if len(list2) == len(list1):
            for i,j in zip(list2,list1):
                diff = i-j
                result.append(diff)
            if result[3] != 0:
                v = [result[0]/result[3],result[1]/result[3],result[2]/result[3]]
                pdu.entityLinearVelocity.x = v[0]
                pdu.entityLinearVelocity.y = v[1]
                pdu.entityLinearVelocity.z = v[2]
                print(icao,v)
                '''Creating a dictionary of velocity_result with key as ICAO and its values as a list of velocities of perticular entity.'''
                if icao not in velocity_result:
                    velocity_result[icao]=[v]
                else:
                    velocity_result[icao].append(v)
                    #print(fid,result)
        else:
            print("list lengths are not same")
                      
def last_position_msg(icao):
    if icao in position_result:
        pobj = position_result[icao]
        p = pobj[len(pobj)-1]
        position_change_with_velocity(icao)
        last_velocity_msg(icao)
        remaining_pdus()
        serialize_pdus()
    else:
        print('no last recorded ecef position')

def last_velocity_msg(icao):        
    if icao in velocity_result:
        vobj = velocity_result[icao]
        v = vobj[len(vobj)-1]
        pdu.entityLinearVelocity.x = v[0]
        pdu.entityLinearVelocity.y = v[1]
        pdu.entityLinearVelocity.z = v[2]
        print('last recorded velocity',pdu.entityLinearVelocity.x,pdu.entityLinearVelocity.y,pdu.entityLinearVelocity.z)
    else:
        print('no last recorded velocity')
    
def position_change_with_velocity(icao):
    if icao in (position_result and velocity_result):
        pobj = position_result[icao]
        p = pobj[len(pobj)-1]
        vobj = velocity_result[icao]
        v = vobj[len(vobj)-1]
        c = [0.2777778*v[0],0.2777778*v[1],0.2777778*v[2]]
        pc = [p[0]+c[0],p[1]+c[1],p[2]+c[2]]
        position_result[icao].append(pc)
        pdu.entityLocation.x = pc[0]
        pdu.entityLocation.y = pc[1]
        pdu.entityLocation.z = pc[2]
        print('position with velocity',pdu.entityLocation.x,pdu.entityLocation.y,pdu.entityLocation.z)
        
def remaining_pdus():
    pdu.exerciseID = 1
    ts = int(time.time())
    pdu.timestamp = ts
    #print('in')                                                        
    pdu.entityID.siteID = 1
    pdu.entityID.applicationID = 1000
    pdu.forceId = 1
    pdu.numberOfVariableParameters = 2
                                                    
                                    
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

def get_orientation(hexstr):
    '''Determining orientation using roll angle (degree), track angle (degree) and magnetic heading (degree)'''
                                    
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
        pdu.entityOrientation.psi = hdg * (pi/180)   #in radians                                 
                                                            

def serialize_pdus():
    memoryStream = BytesIO()
    outputStream = DataOutputStream(memoryStream)
    pdu.serialize(outputStream)
    data = memoryStream.getvalue()
    pdu.length = len(data)
    """I found that the pdu.length variable was not being populated when the pdu was being serialised.
    To get around this I serialised the packet, got the pdulength, inserted this value then re-serialised."""
    memoryStream = BytesIO()
    outputStream = DataOutputStream(memoryStream)
    pdu.serialize(outputStream)
    data1 = memoryStream.getvalue()                 
    udpSocket.sendto(data1, (DESTINATION_ADDRESS, UDP_PORT))
    print ("message sent")

def get_entityID(icao):
    ''' Creating a csv file, to get and set unique entity ID for the aircrafts flying around'''
    with open('/home/pi/open-dis-python-master/src/main/python/dis_network_example/expt.csv', 'r+') as pp:
        csv_file = csv.writer(pp)        
        for i,row in enumerate(pp):
            if icao in row:
                pdu.entityID.entityID = i
                break
        else:
            i = i+1
            csv_file.writerow([icao])
            pdu.entityID.entityID = i
    
if __name__ == "__main__":
    try:
        pdu = EntityStatePdu()
        ser = serial.Serial(port='/dev/ttyUSB0',baudrate=115200,timeout=None, xonxoff=False, rtscts=False, dsrdtr=False)
    
        ser.flushInput()
        ser.flushOutput()
        EID = []
        position_data = { }
        position_result = { }
        velocity_data = { }
        velocity_result = { }
        while True:
            data_raw = ser.read()
            data_left = ser.inWaiting()
            data_raw += ser.read(data_left)

            if len(data_raw) == 18 : 
                short = data_raw[1:15]
                hexstr = short.decode('utf-8')
                icao = adsb.icao(hexstr)
                if icao != None :
                    print('short message',hexstr,icao)
                    get_entityID(icao)
                    mo=get_model_from_icao(icao)
                    if mo!= False :
                        entyp = get_entity_type_from_model(mo)
                        last_position_msg(icao)

            elif len(data_raw) == 32 :
                x = data_raw[1:29]
                hexstr = x.decode('utf-8')                    
                df = pms.df(hexstr)
                icao = adsb.icao(hexstr)
                if icao != None:
                    print('here',hexstr,icao)                            
                    tc = adsb.typecode(hexstr)
                    #print (hexstr,icao,df,tc)
                    msg_even = None
                    msg_odd = None
                    lat_ref = 47.6676454
                    lon_ref = 9.3847333
                                
                    get_entityID(icao)
                    mo=get_model_from_icao(icao)
                    if mo!= False :
                        entyp = get_entity_type_from_model(mo)
                        get_orientation(hexstr)
                                #print (icao,mo)
                        if (df==17 or df==18) and (5<=tc<=18):
                            po = get_ecef_position(hexstr,icao,df,tc)
                            if po != None:
                                vel = aircraft_velocity(po)
                                serialize_pdus()
                        else:
                            last_position_msg(icao)
                        
    except KeyboardInterrupt:
        print('Forced reset')
