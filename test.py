

import bluetooth

server_sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )

port = 0
server_sock.bind(("",port))
server_sock.listen(1)
print( "listening on port", port)

servHost,servPort = server_sock.getsockname()
print("host:",servHost," port:",servPort)


uuid = "1e0ca4ea-299d-4335-93eb-27fcfe7fa848"
"""
print(bluetooth.is_valid_uuid(uuid) )
"""
bluetooth.advertise_service( server_sock, "SampleServer",
                   service_id = uuid,
                   service_classes = [ uuid ]
                    )

"""
client_sock,address = server_sock.accept()
print ("Accepted connection from ",address)

data = client_sock.recv(1024)
print ("received [",data,"]")
"""
server_sock.close()
client_sock.close()