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
import binascii
from tkinter import *
import tkinter.ttk as ttk

##  paramètres du programme

# uuid des services serveur et client
UUID_Serveur = "67b7a1d0-fd7b-11e4-b939-0800200c9a66"
#UUID_Tunnel  = "67b7a1d1-fd7b-11e4-b939-0800200c9a66"

##  variables

#socket du serveur
socketServeur = None
#périphériques directs
peripheriquesContactables = []
peripheriquesAdjacents = []
#mappage réseau à partir de ce point
mappageReseau = {}
mappageService = {}
#recherche
rechercheLancees = 0
origineRecherche = ""

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
        try:
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
            #variable interne
            self.creationReussie = True
        except OSError:
            #erreur dûe à pybluez (pas très descriptive...)
            #variable interne
            self.creationReussie = False
            #defini une valeure bidon d'addresse de serveur
            self.getsockname = lambda: ("XX:XX:XX:XX:XX:XX",0)
            return
        #initialise la liste des connections
        self.connections = []
        #variable interne
        self.actif = True
    
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
            decouverteReseau(sender,adresses)
        elif liste[0] == "recherche":
            #demande de recherche réseau en profondeur
            addresses = [ ( i.split("/")[0] , int(i.split("/")[1]) ) for i in liste[1:] ]
            rechercheReseau(adresses)
        elif liste[0] == "reponse":
            #réponse à une recherche réseau
            #point de départ du retour
            addStart = sender.getsockname()[0]
            #récupère les autres infos
            info = dat[8 + info[8:].find(",") : ]
            items = infos.split(";")
            #envoie ce paquet traité
            reponseRecherche(addStart,items)
    
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
        #change la variable interne
        self.actif = False
        #arrête la pub
        bluetooth.stop_advertising( self )
        #ferme le socket
        bluetooth.BluetoothSocket.close(self)

class SocketTunnel(bluetooth.BluetoothSocket):
    """
        Permet la retransmission d'un service
        dans les deux sens de communication
    """
    
    def __init__(self,addOrigine,serviceInfo):
        """
            crée le tunnel sur le service de "addOrigine"
        """
        #récupère les infos
        self.origine = addOrigine
        
        if serviceInfo["protocol"] == "RFCOMM":
            self.protocole = bluetooth.RFCOMM
        elif serviceInfo["protocol"] == "L2CAP":
            self.protocole = bluetooth.L2CAP
        
        self.port = serviceInfo["port"]
        
        #crée un service correspondant
        bluetooth.BluetoothSocket.__init__(self, self.protocole)
        try:
            self.bind( ("",bluetooth.PORT_ANY) )
        except OSError:
            print("[retransmission de "+self.origine+"] impossible")
            return
        
        #fais de la pub
        bluetooth.advertise_service(self,serviceInfo["name"],
                                         serviceInfo["service-id"],
                                         serviceInfo["service-classes"],
                                         serviceInfo["profiles"])
    
    def begin(self):
        """
            démarre la retransmission d'information
        """
        while True:
            #attend une connexion extérieure
            try:
                print("[retransmission de "+self.origine+"] en attente de connexion")
                extSocket , addresse = self.accept()
            except OSError:
                return
            #tente une connexion vers l'arrivée
            print("[retransmission de "+self.origine+"] connexion de"+addresse)
            socketSortie = bluetooth.BluetoothSocket( self.protocole )
            socketSortie.connect( (self.origine,self.port) )
            #démarre les deux sens de transmission
            self.transArretee = False
            transIn = threading.Thread(target=lambda: self.boucleRetrans(self,socketSortie))
            transIn.daemon = True
            transOut= threading.Thread(target=lambda: self.boucleRetrans(socketSortie,self))
            transOut.daemon = True
            transIn.start()
            transOut.start()
            #attend
            while not self.transArretee:
                time.sleep(1)
            print("[retransmission de "+self.origine+"] arrêt de connexion")
            #ferme les sockets
            extSocket.close()
            socketSortie.close()
        
    def boucleRetrans(self,entree,sortie):
        """
            retransmet des données en boucle, sans s'arrêter
        """
        #boucle de données
        while not self.transArretee:
            d = entree.recv()
            if not d:
                break
            sortie.send(d)
        self.transArretee = True
    
    def close(self):
        """
            ferme le socket
        """
        #ferme le socket
        bluetooth.stop_advertising(self)
        self.close()

## fonctions

def initialisation():
    global socketServeur
    """
        Active la découverte Bluetooth du périphérique,
        et démarre les service appropriés sur les ports.
    """
    socketServeur = SocketServeur(UUID_Serveur)
    
    if socketServeur.creationReussie:
        print("addresse du serveur : ",socketServeur.getsockname() )
    else:
        print("création du socket serveur impossible")
        print("avez vous allumé votre adaptateur bluetooth?")
    
def bouclePrincipale():
    """
        Vérifie en permanence l'activité du serveur
        et démarre de nouveaux threads de dicussion
        quand un client se connecte
    """
    #récupère la variable
    global socketServeur
    #boucle
    while socketServeur.actif:
        #attend des connections
        try:
            extSocket , address = socketServeur.accept()
        except OSError:
            return
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
    #variable interne
    global enCours_rechercheStandard
    enCours_rechercheStandard = True
    majCouleurs()
    #effectue une recherche
    pairs = bluetooth.discover_devices()
    #recherche les périphériques vraiment contactables
    i = 0
    while i<len(pairs):
        p = pairs[i]
        sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        try:
            sock.connect( (p , 19) )
        except OSError:
            print("os error on:",bluetooth.lookup_name(p),p)
            pairs.remove(p)
            i -= 1
        else:
            print("success on:",bluetooth.lookup_name(p),p)
        finally:
            sock.close()
        i += 1
    #associe les noms
    periph = []
    for i in pairs:
        periph.append( (i,bluetooth.lookup_name(i)) )
    #met à jour la liste
    global peripheriquesAdjacents
    peripheriquesAdjacents  = pairs[:]
    #met à jour le mappage
    mappageDepuisListes()
    #màj variable interne
    enCours_rechercheStandard = False
    majCouleurs()
    #retourne la liste nommée
    print("recherche std:",periph)
    return periph

def decouverteReseau(periph=[]):
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
    #variable interne
    global enCours_decouverteReseau
    enCours_decouverteReseau = True
    majCouleurs()
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
    local = rechercheStandard()
    #affecte à la liste locale
    global peripheriquesAdjacents
    peripheriquesAdjacents = liste
    #variables d'état
    enCours_decouverteReseau = False
    majCouleurs()

def mappageDepuisListes():
    """
        Met à jour le mappage, à partir des liste de connections disponibles
    """
    for p in peripheriquesAdjacents:
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
    #représentationdu point de départ
    add = socketServeur.getsockname()[0]
    mappageReseau[add] = {"nom": "origine",
                          "direct": True,
                          "avance": True,
                          "liens": peripheriquesAdjacents[:]}
    #réaffiche la liste
    majListe()

def mappageServiceDepuisListe(liste):
    """
        ajoute les services adjacents trouvés à partir
        d'une recherche de service à la liste
    """
    for item in liste:
        add = item["host"]
        nom = item["name"]
        profiles = item["profiles"]
        sid = item["service-id"]            #inutile : toujours null
        classes = item["service-classes"]
        protocol = item["protocol"]
        port = item["port"]
        raw = item["rawrecord"]
        #extrait l'uuid
        uuid = str(binascii.hexlify( raw.split(b'\t')[3] ))[2:-1]
        uuid = str(uuid[:8]+'-'+uuid[8:12]+'-'+uuid[12:16]+'-'+uuid[16:20]+'-'+uuid[20:32])
        #converti en str les profiles
        profiles = [ (str(i[0])[2:-1],i[1]) for i in profiles ]
        #converti en str les classes
        classes = [ str(i)[2:-1] for i in classes ]
        #converti en str le nom
        if nom: nom = str(nom)[2:-1]
        else:nom = "None"
        #récupère l'élement du mappage
        if add in mappageService:
            periph = mappageService[add]
        else:
            periph = []
            mappageService[add] = periph
        
        #ajoute le service à la liste
        if not (protocol,port) in [ (i["protocol"],i["port"]) for i in periph]:
            periph.append( {"protocol"       : protocol,
                            "name"           : nom,
                            "profiles"       : profiles,
                            "service-id"     : uuid,
                            "service-classes": classes,
                            "port"           : port} )
            print("proto ",item["name"],"has uuid:",sid)
            print("service id:",item["profiles"]," classes",item["service-classes"])

def mappageDepuisStr(str,origine):
    """
        ajoute des périphériques au réseau à partir d'une chaine de
        caractère. Prend comme point de réduction de ces périphériques
        l'adresse "origine"
    """
    #sépare les infos
    infos = str.split(",")
    add = infos[0]
    nom = infos[1]
    direct = bool( infos[2] )
    avance = bool( infos[3] )
    liens = infos[4][1:-1]
    #trouve l'élément d'origine
    if origine in mappageReseau.keys():
        oItem = mappageReseau[add]
    else:
        oItem = {}
    if direct:
        if not add in oItem["liens"]:
            oItem["liens"].append(add)
    #trouve l'élément spécifié
    if add in mappageReseau.keys():
        item = mappageReseau[add]
    else:
        item = {"liens":[]}
    #mise à jour des infos
    item["nom"] = nom
    item["direct"] = add in peripheriquesAdjacents
    item["avance"] = avance
    for l in liens:
        if not l in item["liens"]:
            item["liens"].append(l)
    #réaffiche la liste
    majListe()

def rechercheReseau(origine="",periph=[]):
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
    #variable interne
    global enCours_rechercheReseau
    enCours_rechercheReseau = True
    majCouleurs()
    #cherche tous les services à proximité
    print("trouve les service")
    services = bluetooth.find_service()
    #recherche les périphériques à proximité qui ont ce programme
    liste = []
    for item in services:
        if item["service-id"] == UUID_Serveur:
            liste.append( item["host"] )
    print("trouvé : ",liste)
    #affecte à la liste locale
    global peripheriquesContactables
    peripheriquesContactables = liste
    mappageServiceDepuisListe(services)
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
        socketServeur.envoiePaquet( add , "recherche," + arg )
        rechercheLancees += 1
    #effectue une recherche locale
    local = rechercheStandard() #mappage màj en mm temps
    #attends les réponses
    print("attends retour...")
    while rechercheLancees > 0:
        time.sleep(0.1)
    #retourne à l'envoyeur
    if origine != "":
        #crée une chaine de réponse
        argAdj = ";".join( [ strDepuisMappage(a) for a in mappageReseau.keys() ] )
        #envoie cette réponse
        socketServeur.envoiePaquet(origine,"reponse," + arg )
    #màj variable interne
    enCours_rechercheReseau = False
    majCouleurs()

def strDepuisMappage(address):
    """
        donne la représentation sous forme de chaine de caractère
        d'un objet du mappage
    """
    item = mappageReseau[address]
    #infos de base
    str = address+","+item["nom"]+","+str(int(item["direct"]))+","+str(int(item["avance"]))
    #liens
    str += ",[" + ".".join( item["liens"] ) + "]"
    
    return str

def reponseRecherche(origine,items):
    """
        traite les informations relatives à un retour de recherche
    """
    #réponse à une recherche
    global rechercheLancees
    rechercheLancees -= 1
    #ajout des items au mappage
    for i in items:
        mappageDepuisStr(i,origine)

def extraitAddresses(carte):
    """
        extrait toute les adresses présentes sur
        une carte sous forme de liste
        
        exemple:
           pour carte = 
             { "<add1>" : { "<add2>" : {},
                            "<add3>" : {}},
               "<add4>" : { "<add5>" : {},
                            "<add6>" : {},
                            "<add7>" : {}}}
          donne: ["<add1>","<add2>", ... ,"<add7>"]
    """
    listeAdd = []
    for k in carte.keys():
        listeAdd.append(k)
        listeAdd.extend( extraitAddresses(carte[k]) )
    return listeAdd

def carteSimplifiee(depart=None,interdits=[]):
    """
        crée à partir de "mappageReseau" une carte
        partant du point de départ sans inclure les interdits
        
        /!\ n'inclut que les périphériques avancés (avec programme)
        
        exemple:
        
          réseau:
                              __________________ add5 __
                   add2 \    /                   /      \
                          add1 --- départ --- add4 --- add6
                   add3 /                        \
                                                add7
                                                
        forme de la liste:
             { "<add1>" : { "<add2>" : {},
                            "<add3>" : {}},
               "<add4>" : { "<add5>" : {},
                            "<add6>" : {},
                            "<add7>" : {}}}
    """
    #récupère l'adresse du serveur actuel
    add = socketServeur.getsockname()[0]
    if not depart:
        depart = add
    #copie les interdits, pour ne pas les modifier
    interdits2 = interdits[:]
    interdits2.append( add )
    #récupère les liens actuels
    liens = mappageReseau[depart]["liens"]
    #crée le dictionnaire à retourner
    connexions = {}
    #parcoure le mappage réseau
    for l in liens:
        if mappageReseau[l]["avance"]:
            #actualise les interdits pour cette recherche
            interditsActuels = interdits2[:]
            liensMod = liens[:]
            liensMod.remove(l)
            interditsActuels.extend(liensMod)
            #démarre une nouvelle recherche à partir de l
            carteL = carteSimplifiee(l,interditsActuels)
            #ajout au dictionnaire
            connexions[l] = carteL
            #ajout des adresses parcourues aux interdits
            interdits2.extend( extraitAddresses(carteL) )
    #retourne la carte
    return connexions

## Interface graphique

#variables d'état : action en cours
enCours_decouverteReseau = False
enCours_rechercheStandard = False
enCours_rechercheReseau = False
enCours_affichageReseau = False
#interface initialisé
interfaceInitialise = False

#objets de l'interface
bt_decouverte = None
bt_rechercheStd = None
bt_rechercheAv = None
bt_affichage = None
bt_retransmission = None
bt_quitter = None
liste_peripheriques = None

#addresse d'origine de la retransmission
addresseSelectionnee = None

def afficheReseau():
    """
        affiche une carte du réseau
    """
    #récupère la carte simplifiée des noeuds
    carte = carteSimplifiee()
    print(carte)
    
#fonctions de lancement de threads
def startDecouverteReseau():
    """
        démarre un thread de découverte du réseau
    """
    if interfaceInitialise and socketServeur.creationReussie:
        global enCours_decouverteReseau
        if not enCours_decouverteReseau:
            enCours_decouverteReseau = True
            t = threading.Thread( target = decouverteReseau )
            t.daemon = True
            t.start()
        majCouleurs()

def startRechercheStandard():
    """
        démarre un thread de recherche standard
    """
    if interfaceInitialise and socketServeur.creationReussie:
        global enCours_rechercheStandard
        if not enCours_rechercheStandard:
            enCours_rechercheStandard = True
            t = threading.Thread( target = rechercheStandard )
            t.daemon = True
            t.start()
        majCouleurs()
        
def startRechercheReseau():
    """
        démarre un thread de recherche réseau
    """
    if interfaceInitialise and socketServeur.creationReussie:
        global enCours_rechercheReseau
        if not enCours_rechercheReseau:
            enCours_rechercheReseau = True
            t = threading.Thread( target = rechercheReseau )
            t.daemon = True
            t.start()
        majCouleurs()

def pressListRetransmettre(listePeriph,listeServices):
    #récupère la sélection
    if len(listePeriph.curselection()) < 1:
        return
    sel = listePeriph.curselection()[0]
    add = listePeriph.get(sel)
    #variable interne
    global addresseSelectionnee
    addresseSelectionnee = add
    #màj la liste des services
    it = mappageService[add]
    listeServices.delete(0, listeServices.size() )
    for s in it:
        listeServices.insert(END,s["name"]+" : "+s["protocol"]+","+str(s["port"]) )
    
def pressBtOkRetransmettre(listePeriph,listeServices):
    """
        démarre la retransmission d'un service
    """
    #récupère le service
    if len(listeServices.curselection()) < 1:
        return
    sel = int(listeServices.curselection()[0])
    item = mappageService[addresseSelectionnee][sel]
    print("démarre une retransmission de:")
    print(addresseSelectionnee)
    print("service:")
    print(item)
    startRetransmission(addresseSelectionnee,sel)

def startRetransmission(add,num):
    """
        démarre un thread de retransmission,
        avec une petite fenêtre
    """
    #récupère le service
    item = mappageService[add][num]
    #fenetre
    fen = Toplevel()
    info = Label(fen,text="Retransmission...")
    info.pack()
    info2 = Label(fen,text="origine : "+add)
    info2.pack()
    info3 = Label(fen,text="nom : "+item["name"])
    info3.pack()
    info4 = Label(fen,text="protocole : "+item["protocol"]+" : "+str(item["port"]))
    info4.pack()
    #socket de retransmission
    retrans = SocketTunnel(add,item)
    #démarre le thread
    t = threading.Thread(target = retrans.begin)
    t.daemon = True
    t.start()

def configRetransmettre():
    """
        ouvre une fenètre de configuration
        de retransmission d'un service
    """
    fen = Toplevel()
    #labels
    listTxt = Label(fen,text="choix du périphérique")
    list2Txt = Label(fen,text="choix du service")
    #liste des peripheriques
    list = Listbox(fen,width=100)
    for i in mappageService.keys():
        list.insert(END,i)
    #liste des services
    list2 = Listbox(fen,width=100)
    #boutons
    validerPeriph = Button(fen,text="Choisir",command = lambda: pressListRetransmettre(list,list2))
    annuler = Button(fen,text="Annuler",command = fen.destroy )
    valider = Button(fen,text="Ok",command = lambda: pressBtOkRetransmettre(list,list2) )
    #affecte le double-clic
    list.bind("Double-Button-1",lambda: pressListRetransmettre(list,list2))
    #ajustement dans la fenetre
    listTxt.grid(row=0,column=0)
    list.grid(row=0,column=1,rowspan=2,columnspan=2)
    validerPeriph.grid(row=1,column=0)
    list2Txt.grid(row=2,column=0)
    list2.grid(row=2,column=1,columnspan=2)
    annuler.grid(row=3,column=1)
    valider.grid(row=3,column=2)

#fonctions de mise à jour des widgets
def majCouleurs():
    """
        met à jour les couleurs des boutons
        en fonctions des activités en cours
    """
    if interfaceInitialise:
        global enCours_decouverteReseau,bt_decouverte
        if enCours_decouverteReseau:
            bt_decouverte.configure(bg="yellow")
        else:
            bt_decouverte.configure(bg="SystemButtonFace")
            
        global enCours_rechercheStandard,bt_rechercheStd
        if enCours_rechercheStandard:
            bt_rechercheStd.configure(bg="yellow")
        else:
            bt_rechercheStd.configure(bg="SystemButtonFace")
            
        global enCours_rechercheReseau,bt_rechercheAv
        if enCours_rechercheReseau:
            bt_rechercheAv.configure(bg="yellow")
        else:
            bt_rechercheAv.configure(bg="SystemButtonFace")

def majListe():
    if interfaceInitialise:
        global liste_peripheriques
        #supprime tous les éléments
        e = liste_peripheriques.get_children()
        for i in e:
            liste_peripheriques.delete(i)
        #recrée tous les éléments
        for k in mappageReseau.keys():
            item = mappageReseau[k]
            type = "normal"
            if item["avance"]:
                type = "avancé"
                
            if item["nom"] == "origine":
                type = "départ"
                
            liste_peripheriques.insert('',"end",values=(k,item["nom"],type ),tags=(type))
        liste_peripheriques.tag_configure('normal', background='white')
        liste_peripheriques.tag_configure('avancé', background='purple')
        liste_peripheriques.tag_configure('départ', background='blue')

#crée la fenètre
def menu(fenetre):
    #variables
    global bt_decouverte
    global bt_rechercheStd
    global bt_rechercheAv
    global bt_affichage
    global bt_retransmission
    global bt_quitter
    global liste_peripheriques
    #création des boutons
    bt_decouverte = Button(fenetre, text = "Découverte", command = startDecouverteReseau)
    bt_rechercheStd = Button(fenetre, text = "Recherche standard", command = startRechercheStandard)
    bt_rechercheAv = Button(fenetre, text = "Recherche avancée", command = startRechercheReseau)
    bt_affichage = Button(fenetre, text = "Mappage reseau", command = lambda: afficheReseau())
    bt_affichage.config(bg="grey")
    bt_retransmission = Button(fenetre, text= "Retransmettre un service", command = configRetransmettre )
    bt_quitter = Button(fenetre, text = "Quitter", command = fenetre.destroy)
    #création de la vue sous-forme de liste
    liste_peripheriques = ttk.Treeview(fenetre, columns = ("addresse","nom","type"),show = "headings")
    liste_peripheriques.heading("addresse",text = "adresse")
    liste_peripheriques.heading("nom",text = "nom")
    liste_peripheriques.heading("type",text = "type")
    
    #ajout à la fenètre
    bt_decouverte.grid(row=0,sticky=W+E)
    bt_rechercheStd.grid(row=1,sticky=W+E)
    bt_rechercheAv.grid(row=2,sticky=W+E)
    bt_affichage.grid(row=3,sticky=W+E)
    bt_retransmission.grid(row=4,sticky=W+E)
    bt_quitter.grid(row=5,sticky=W+E)
    liste_peripheriques.grid(column=1,row=0,rowspan=6)
    
    #variable d'état
    global interfaceInitialise
    interfaceInitialise = True
    #affichage à l'écran
    fenetre.mainloop()
    
## début du programme

#démarre le serveur
initialisation()

#démarre l'acceptation de connections
main = threading.Thread(target = bouclePrincipale)
main.daemon = True
main.start()

#création de la fenetre
fenetre = Tk()
fenetre.title("Bluetooth routing")

menu(fenetre)

#ferme le serveur
socketServeur.close()

    




