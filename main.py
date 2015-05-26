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
    transmettre des données par la connection tunnel.

    Ce programme utilise la bibliothèque pybluez

    versions:
        python 3.3.5
        pybluez 0.20 for python 3.3
        
        
    :var mappageReseau:
          dictionnaire de toutes les addresses connues de ce point
          où chaque entrée est repéree par son adresse MAC
          
          attributs:
            nom : nom lisible du périphérique
            direct : le périphérique est-il visible d'ici
            avance : le périphérique a-t-il un serveur
            liens : périphériques contactables à travers celui-ci
          
        exemple de dictionnaire:
          {
            "XX:XX:XX:XX:00" : {"nom": "ordi1" ,
                                "direct": True ,
                                "avance": True,
                                "liens": <liste de proximité de ordi1>} ,
            "XX:XX:XX:XX:01" : {"nom": "ordi2" ,
                                "direct": False ,
                                "avance": True,
                                "liens": <liste de proximité de ordi2>} ,
            "XX:XX:XX:XX:02" : {"nom": "telephone" ,
                                "direct": False ,
                                "avance": False,
                                "liens": <liste de proximité de telephone>}
          }
"""

import bluetooth
import threading
import time

##  paramètres du programme

# uuid des services serveur et client
UUID_Serveur = "67b7a1d0-fd7b-11e4-b939-0800200c9a66"
UUID_Tunnel  = "67b7a1d1-fd7b-11e4-b939-0800200c9a66"

##  variables

#socket du serveur
socketServeur = None
#recherches
peripheriquesContactables = []
peripheriquesAdjacents = []
rechercheLancees = 0
#mappage réseau à partir de ce point
mappageReseau = {}

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
        # commence l'écoute sur le port, avec une connection
        # en file d'attente au maximum
        self.listen(1)
        # averti le serveur SDP de la présence du serveur
        bluetooth.advertise_service( self, "Paquet",uuid,[uuid])
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
                p = tampon.find(";")
                tailleMessage = int(l[:p])
                tampon = l[p:]
            #attend d'avoir reçu un paquet entier
            if tailleMessage:
                if len( tampon ) >= tailleMessage:
                    self.utilisePaquet(sock,tampon[:tailleMessage])
                    tampon = tampon[tailleMessage:]
        
    def utilisePaquet(self,sender,dat):
        """
            interprète les données d'un paquet reçu
        """
        print("recu paquet:\n",dat)
        liste = dat.split(",")
        if liste[0] == "decouverte":
            #demande de découverte réseau en profondeur
            addresses = [ ( i.split("/")[0] , int(i.split("/")[1]) ) for i in liste[1:] ]
            decouverteReseau(adresses)
    
    def envoiePaquet(self,dest,dat):
        """
            Permet d'envoyer un paquet de donnée à un destinataire
            
            :param dest: tuple de forme (host,channel)
        """
        #trouve la taille du paquet
        tailleMessage = len( bytes(dat,encoding="utf-8") )
        #crée le paquet
        message = str(tailleMessage) + ";" + dat
        #ouvre une connection
        sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        sock.connect( (dest[0] , bluetooth.PORT_ANY) )
        #envoie le message
        sock.send(message)
        #ferme la connection
        sock.close()
    
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
        #attend des connections
        extSocket , address = socketServeur.accept()
        #ajoute la connection à la liste actuelle
        socketServer.connections.append( [ address , extSocket ] )
        #démarre un thread de discussion
        dat = threading.Thread(target = socketServeur.serveurDataThread,args = [extSocket])
        dat.daemon = True
        dat.start()

def rechercheStandard():
    """
        Effectue une recherche rapide (sans contacter
        les autres périphériques)
    """
    #effectue une recherche
    pairs = bluetooth.discover_devices()
    #associe les noms
    periph = []
    for i in pairs:
        periph.append( (i,bluetooth.lookup_name(i)) )
    #met à jour la liste
    global peripheriquesAdjacents
    peripheriquesAdjacents  = pairs[:]
    #met à jour le mappage
    mappageDepuisListes()
    #retourne la liste nommée
    return periph

def decouverteReseau(periph):
    """
        Permet d'accéder à tous les périphériques à proximité qui
        possèdent le service de réseau actif, et leurs demander
        d'effectuer à leur tour une découverte réseau.
        
        La découverte s'effectue en deux temps:
          1 - élements contactables:
              trouve les périphériques pouvant mapper le réseau
              (avec le service démarré)
          2 - élements atteignables:
              affecte à chaque periphérique actif une liste
              d'autres périphériques qu'il peut atteindre
        
        Cette recherche peut prendre du temps
        
        :param periph: liste des périphériques déjà découverts
                       sous forme d'un tuple ( adresse MAC , port RFCOMM )
        
        :return: None
    """
    #recherche les périphériques à proximité qui ont ce programme
    print("trouve le service")
    liste = bluetooth.find_service("Paquet",UUID_Serveur)
    print("trouvé : ",liste)
    liste = [ i["host"] for i in liste ]
    #affecte à la liste locale
    global peripheriquesContactables
    peripheriquesContactables = liste[:]
    #ajoute l'adresse actuelle à la liste
    periph.append( socketServeur.getsockname() )
    #supprime les éléments déjà inspectés
    for item in liste:
        if item[0] in periph:
            liste.remove(item)
    #crée l'argument du paquet de recherche
    arg = ",".join( [ item[0] + "/" + str(item[1]) for item in liste ] )
    #demande aux periphériques d'effectuer leur recherche
    for add in liste:
        socketServeur.envoiePaquet( add , "decouverte," + arg )
    #effectue une recherche locale
    local = listeStandard(time)
    #affecte à la liste locale
    global peripheriquesAdjacents
    peripheriquesAdjacents = liste

def mappageDepuisListes():
    """
        Met à jour le mappage, à partir des liste de connections disponibles
    """
    for p in peripheriquesAdjacent:
        #crée un nouvel élément
        item = { "nom": bluetooth.lookup_name(p) ,
                 "direct": True ,
                 "avance": p in peripheriquesContactables,
                 "liens": [] }
        #modifie si déjà ds le mappage actuel
        if p in mappageReseau.keys():
            item["liens"] = mappageReseau[p]["liens"]
        #ajout au mappage
        mappageReseau[p] = item

def rechercheReseau(periph):
    """
        Permet d'accéder à tous les périphériques à proximité qui
        possèdent le service de réseau actif, et leurs demander
        d'effectuer à leur tour une recherche réseau.
        
        La recherche s'effectue en deux temps:
          1 - élements actifs:
              trouve les périphériques pouvant mapper le réseau
          2 - élements atteignables:
              affecte à chaque periphérique actif une liste
              d'autres périphériques qu'il peut atteindre
        
        Cette recherche peut prendre du temps
        
        :param periph: liste des périphériques déjà découverts
                       sous forme d'adresse MAC
        :param time: temps maximum de la recherche
        
        :return: None
    """
    #recherche les périphériques à proximité qui ont ce programme
    print("trouve le service")
    liste = bluetooth.find_service("Paquet",UUID_Serveur)
    print("trouvé : ",liste)
    liste = [ i["host"] for i in liste ]
    #affecte à la liste locale
    global peripheriquesContactables
    peripheriquesContactables = liste
    #ajoute l'adresse actuelle à la liste
    periph.append( socketServeur.getsockname() )
    #supprime les éléments déjà inspectés
    for item in liste:
        if item[0] in periph:
            liste.remove(item)
    #crée l'argument du paquet de recherche
    arg = ",".join( [ item[0] + "/" + str(item[1]) for item in liste ] )
    #demande aux periphériques d'effectuer leur recherche
    global rechercheLancees
    rechercheLancee = 0
    for add in liste:
        socketServeur.envoiePaquet( add , "decouverte," + arg )
        rechercheLancees += 1
    #effectue une recherche locale
    local = listeStandard() #mappage màj en mm temps
    #attends les réponses
    print("attends retour...")
    while rechercheLancees > 0:
        time.sleep(0.1)

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
    print(" 1) découverte:")
    print("     demande à chaque périphérique du réseau")
    print("     d'effectuer une recherche")
    print(" 2) recherche standard:")
    print("     trouve tous les périphériques contactables")
    print("     à proximité")
    print(" 3) recherche avancée:")
    print("     trouve tous les périphériques contactables")
    print("     à travers le réseau")
    print(" 4) mappage réseau:")
    print("     affiche une carte du réseau")
    print(" 5) quitter")
    
    k = input(":")
    try:
        k = int(k)
    except:
        print("\nentrez un nombre...\n")
    else:
        if k < 1 or k > 4:
            print("\nentrez un vrai choix\n")
        else:
            if k == 1:
                #demande à chaque périphérique de découvrir son réseau
                decouverteReseau([])
            elif k == 2:
                #découverte bluetooth standard
                liste = rechercheStandard()
                print(liste)
            elif k == 3:
                #découverte bluetooth avancée
                rechercheReseau()
            elif k == 4:
                #cherche les amis, pour donner une carte
                pass
            elif k == 5:
                #quitter :-(
                continuer = False

#ferme le serveur
socketServeur.close()


