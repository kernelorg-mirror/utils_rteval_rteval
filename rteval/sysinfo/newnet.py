# SPDX-License-Identifier: GPL-2.0-or-later
''' Module to obtain network information for the rteval report '''
#
#   Copyright 2022 - 2025 John Kacur <jkacur@redhat.com>
#

import os
import socket
import ipaddress
import sys
import libxml2
from rteval.Log import Log

def get_active_devices():
    ''' returns a list of active network devices, similar to ethtool '''
    ret = []

    for device in socket.if_nameindex():
        ret.append(device[1])

    return ret

def compress_iv6(addr):
    ''' inserts colons into an ipv6address and returns it in compressed form '''
    retaddr = ''
    # Insert colons into the number
    for i in range(4,33,4):
        if i == 32:
            retaddr += addr[i-4:i]
        else:
            retaddr += addr[i-4:i] + ':'
    addr = ipaddress.IPv6Network(retaddr)
    retaddr = str(ipaddress.IPv6Address(retaddr))
    return retaddr

def get_defaultgw():
    ''' return the ipv4address of the default gateway '''
    defaultgw = None
    with open('/proc/net/route') as f:
        line = f.readline().strip()
        while len(line) > 0:
            (iface, dest, gateway, _, _, _, _, _, _, _, _) = line.split()
            if iface == 'Iface':
                line = f.readline().strip()
                continue
            if dest == '00000000' and gateway != '00000000':
                addr = int(gateway, base=16)
                defaultgw = str(ipaddress.IPv4Address(socket.ntohl(addr)))
                return defaultgw
            line = f.readline().strip()
    return defaultgw

class IPv6Addresses():
    ''' Obtains a list of IPv6 addresses from the proc file system '''

    def __init__(self):
        self.data = {}
        IPv6Addresses.load(self)

    def __contains__(self, dev):
        return dev in self.data

    def __getitem__(self, dev):
        return self.data.get(dev, None)

    def __iter__(self):
        return iter(self.data)

    def load(self):
        '''
            Called by init to load the self.data dictionary with device keys
            and a list of ipv6addresses
        '''
        MYP = '/proc/net/if_inet6'
        try:
            with open(MYP, 'r') as f:
                mystr = f.readline().strip()
                while len(mystr) > 0:
                    ipv6addr , _, _, _, _, intf = mystr.split()
                    ipv6addr = compress_iv6(ipv6addr)
                    if intf == 'lo':
                        mystr = f.readline().strip()
                        continue
                    if intf not in self.data:
                        self.data[intf] = [ipv6addr]
                    else:
                        self.data[intf].append(ipv6addr)
                    mystr = f.readline().strip()
        # if IPv6 is disabled, the if_net6 files does not exist, so we can pass
        except FileNotFoundError:
            pass

class IPv4Addresses():
    ''' Obtains a list of IPv4 addresses from the proc file system '''

    def __init__(self):
        self.data = {}
        IPv4Addresses.load(self)

    def __contains__(self, dev):
        return dev in self.data

    def __getitem__(self, dev):
        return self.data[dev]

    def __iter__(self):
        return iter(self.data)

    def load(self):
        '''
            Called by init to load the self.data dictionary with
            device keys, and value consisting of a list of
            ipv4address, netmask and broadcast address
        '''
        MYP = '/proc/net/route'
        with open(MYP, 'r') as f:
            mystr = f.readline().strip()
            while len(mystr) > 0:
                intf, dest, _, _, _, _, _, mask, _, _, _ = mystr.split()
                # Skip over the head of the table an the gateway line
                if intf == "Iface" or dest == '00000000':
                    mystr = f.readline().strip()
                    continue
                d1 = int(dest, base=16)
                m1 = int(mask, base=16)
                addr = str(ipaddress.IPv4Address(socket.ntohl(d1)))
                netmask = str(ipaddress.IPv4Address(socket.ntohl(m1)))
                addr_with_mask = ipaddress.ip_network(addr + '/' + netmask)
                broadcast = str(addr_with_mask.broadcast_address)
                if intf not in self.data:
                    self.data[intf] = [(addr, netmask, broadcast)]
                else:
                    self.data[intf].append((addr, netmask, broadcast))
                mystr = f.readline().strip()


class MacAddresses():
    ''' Obtains a list of hardware addresses of network devices '''

    def __init__(self):
        self.mac_address = {}
        self.path = None
        MacAddresses.load(self)

    def load(self):
        '''
            called by init to load self.mac_address as a dictionary of
            device keys, and mac or hardware addresses as values
        '''
        nics = get_active_devices()
        for nic in nics:
            self.path = f'/sys/class/net/{nic}'
            hwaddr = MacAddresses.set_val(self, 'address')
            self.mac_address[nic] = hwaddr

    def set_val(self, val):
        ''' Return the result of reading self.path/val '''
        val_path = f'{self.path}/{val}'
        if os.path.exists(val_path):
            with open(val_path, 'r') as f:
                return f.readline().strip()
        return None

    def __contains__(self, dev):
        return dev in self.mac_address

    def __getitem__(self, dev):
        return self.mac_address[dev]

    def __iter__(self):
        return iter(self.mac_address)

class NetworkInfo():
    ''' Creates an xml report of the network for rteval '''

    def __init__(self, logger):
        self.defgw4 = get_defaultgw()
        self.__logger = logger

    def MakeReport(self):
        ''' Make an xml report for rteval '''
        ncfg_n = libxml2.newNode("NetworkConfig")
        defgw4 = self.defgw4

        mads = MacAddresses()
        for device in mads:
            if device == 'lo':
                continue
            intf_n = libxml2.newNode('interface')
            intf_n.newProp('device', device)
            intf_n.newProp('hwaddr', mads[device])
            ncfg_n.addChild(intf_n)

            ipv4ads = IPv4Addresses()
            ipv6ads = IPv6Addresses()
            for dev in ipv4ads:
                if dev != device:
                    continue
                for lelem in ipv4ads[dev]:
                    ipv4_n = libxml2.newNode('IPv4')
                    (ipaddr, netmask, broadcast) = lelem
                    ipv4_n.newProp('ipaddr', ipaddr)
                    ipv4_n.newProp('netmask', netmask)
                    ipv4_n.newProp('broadcast', broadcast)
                    ipv4_n.newProp('defaultgw', (defgw4 == ipaddr) and '1' or '0')
                    intf_n.addChild(ipv4_n)
                if ipv6ads[dev]:
                    for lelem in ipv6ads[dev]:
                        ipv6_n = libxml2.newNode('IPv6')
                        ipaddr = lelem
                        ipv6_n.newProp('ipaddr', ipaddr)
                        intf_n.addChild(ipv6_n)
        return ncfg_n

if __name__ == "__main__":

    try:
        log = Log()
        log.SetLogVerbosity(Log.DEBUG|Log.INFO)
        net = NetworkInfo(logger=log)
        doc = libxml2.newDoc('1.0')
        cfg = net.MakeReport()
        doc.setRootElement(cfg)
        doc.saveFormatFileEnc('-', 'UTF-8', 1)

    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print(f"** EXCEPTION {str(e)}")
