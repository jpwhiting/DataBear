'''
Testing out selectors and a socket
'''
import socket
import selectors
import threading
import time

sel = selectors.DefaultSelector()

#-------- Main Class -------
class looper:

    def __init__(self):
        '''
        Create socket and start thread
        '''
        self.udpsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.udpsocket.bind(('localhost',62000))
        self.udpsocket.setblocking(False)
        sel.register(self.udpsocket,selectors.EVENT_READ)

    def listenUDP(self):
        while self.listen:
            #Check for UDP comm
            event = sel.select(timeout=0)
            if event:
                print(self.readUDP())

    
    def readUDP(self):
        '''
        Read message, respond, add message to list
        '''
        msg, address = self.udpsocket.recvfrom(1024)
        print('Got message from {}: {}'.format(address,msg))
        self.udpsocket.sendto('Yes I hear you'.encode('utf-8'),address)
        
        return 'Got one!'

    def run(self):
        '''
        Run loop doing work and looking for messages
        '''
        self.listen = True
        t = threading.Thread(target=self.listenUDP)
        t.start()

        while True:
            try:
                print('Im working')
                time.sleep(2)
            except KeyboardInterrupt as ki:
                self.listen=False
                print('Shutting down')
                break

if __name__ == "__main__":
    myloop = looper()
    myloop.run()


