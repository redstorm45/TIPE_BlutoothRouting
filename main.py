# -*- coding: utf-8 -*-

"""

    Ce projet est un essai de routage similaire à celui du web,
    mais appliqué au bluetooth.

    Le routeur est un programme hôte des périphériques,
    permettant un mappage réseau (découverte réseau),
    et du transfert de donnée d'un réseau à un autre.

    Tous les périphériques possèdent un port utilisé par le serveur,
    et un autre pour le tunnel. Ainsi, il se connecte à tous les
    périphériques qu'il trouve à proximité avec ce protocole, et peut
    transmettre des données par la connexion tunnel.

    Ce programme utilise la bibliothèque pybluez

    versions:
        python 3.3.5
        pybluez 0.20 for python 3.3

"""

import bluetooth
import threading

##  paramètres du programme

# uuid des services serveur et client
UUID_Serveur = "67b7a1d0-fd7b-11e4-b939-0800200c9a66"
UUID_Tunnel  = "67b7a1d1-fd7b-11e4-b939-0800200c9a66"

##  variables

#socket du serveur
socketServeur = None

## classe

class SocketServeur(bluetooth.BluetoothSocket):
    """
        Classe qui permet de lancer l'application
        sur l'un des ports du périphérique
    """
    
    def __init__(self,uuid):
        """
            Permet de créer un socket serveur
        """
        # initialise un socket RFCOMM
        bluetooth.BluetoothSocket.__init__( self, bluetooth.RFCOMM )
        # applique le socket sur le premier adaptateur trouvé,
        # et le premier port libre
        self.bind( ("",bluetooth.PORT_ANY) )
        # commence l'écoute sur le port, avec 1 connexion
        # en file d'attente au maximum
        self.listen(1)
        # averti le serveur SDP de la présence du serveur
        bluetooth.advertise_service( self, "Packet",uuid,[uuid])
        #initialise la liste des connections
        self.connections = []
    
    def serveurDataThread(self,sock):
        """
            permet l'attente de données entrantes sur le socket
            sans arreter le reste du code
        """
        tampon = ""
        tailleMessage = None
        #tant que des données arrivent
        while True:
            #reçoit des données
            dat = sock.recv()
            #ferme si plus de données
            if not dat:
                break
            #ajoute les données au tampon
            tampon += dat
            #recupère la taille requise
            if ":" in tampon and not tailleMessage:
                l = tampon.split(":")
                tailleMessage = int(l[0])
                tampon = l[1]
            #attend d'avoir reçu un paquet entier
            if tailleMessage:
                if len( tampon ) >= tailleMessage:
                    self.utilisePaquet(sock,tampon[:tailleMessage])
                    tampon = tampon[tailleMessage:]
    
    def utilisePaquet(self,sender,dat):
        """
            interprète les données d'un paquet reçu
        """
    
    def close(self):
        """
            ferme le socket serveur et arrête le service attaché
        """
        #arrête la pub
        bluetooth.stop_advertising( self )
        #ferme le socket
        bluetooth.BluetoothSocket.close(self)

## fonctions

def initialisation():
    global socketServeur
    """
        Active la découverte Bluetooth du périphérique,
        et démarre les service appropriés sur les ports.
    """
    socketServeur = SocketServeur(UUID_Serveur)
    
    print("addresse du serveur : ",socketServeur.getsockname() )
    
def bouclePrincipale():
    """
        Vérifie en permanence l'activité du serveur
        et démarre de nouveaux threads de dicussion
        quand un client se connecte
    """
    #récupère la variable
    global socketServeur
    #boucle
    while True:
        #attend des connexions
        extSocket , address = socketServeur.accept()
        #ajoute la connection à la liste actuelle
        socketServer.connections.append( [ address , extSocket ] )
        #démarre un thread de discussion
        dat = threading.Thread(target = socketServeur.serveurDataThread,args = [extSocket])
        dat.daemon = True
        dat.start()

def decouverteReseau(periph,time=5):
    """
        Permet d'accéder à tous les périphérques à proximité qui
        possèdent le service de réseau actif, et leurs demander
        d'effectuer à leur tour une recherche réseau.
        
        La recherche s'effectue en deux temps:
          1 - élements actifs:
              trouve les périphériques pouvant mapper le réseau
          2 - élements atteignables:
              affecte à chaque periphérique actif une liste
              d'autres périphériques qu'il peut atteindre
        
        :param periph: liste des périphériques déjà découverts
                       sous forme d'adresse MAC
        :param time: temps maximum de la recherche
        
        :return: None
    """

def listeComplet():
    """
        Donne une liste complète des périphériques du réseau
        
        :return: liste des éléments par leur adresses
            
        :example:
            
            réseau comme suit: (D0 point de départ)
            
                    D0 --- D1
                      \--- D2 --- D3
            
            return:
                [ 
                  { 
                    "nom" : "D1",
                    "adress" : "XX:XX:XX:XX:X1"
                  } ,
                  { 
                    "nom" : "D2",
                    "adress" : "XX:XX:XX:XX:X2"
                  } ,
                  { 
                    "nom" : "D3",
                    "adress" : "XX:XX:XX:XX:X3"
                  }
                ]
        
    """
    
def mappageComplet():
    """
        Donne une carte complète du réseau,
        sous forme de dictionnaires imbriqués
        
        :return: liste des éléments par leur adresses
        
        :example:
            
            réseau comme suit: (D0 point de départ)
            
                    D0 --- D1
                      \--- D2 --- D3
            
            return:
                [ 
                  { 
                    "nom" : "D1",
                    "adress" : "XX:XX:XX:XX:X1"
                  } ,
                  { 
                    "nom" : "D2",
                    "adress" : "XX:XX:XX:XX:X2",
                    "pairs" : 
                    [
                      { 
                        "nom" : "D3",
                        "adress" : "XX:XX:XX:XX:X3"
                      }
                    ]
                  }
                ]
        
    """


## début du programme

#démarre le serveur
initialisation()

#démarre l'acceptation de connections
main = threading.Thread(target = bouclePrincipale)
main.daemon = True
main.start()

#boucle principale
continuer = True
while continuer:
    print("   **** MENU ****   ")
    print(" 1) découverte standard")
    print(" 2) découverte avancée")
    print(" 3) mappage réseau")
    print(" 4) quitter")
    
    k = input("press enter to end")
    try:
        k = int(k)
    except:
        print("\nentrez un nombre...\n")
    else:
        if k < 1 or k > 4:
            print("\nentrez un vrai choix\n")
        else:
            if k == 1:
                #découverte bluetooth standard
                pass
            elif k == 2:
                #découverte multi-étage
                pass
            elif k == 3:
                #cherche les amis, pour donner une carte
                pass
            elif k == 4:
                #quitter :-(
                continuer = False

#ferme le serveur
socketServeur.close()


