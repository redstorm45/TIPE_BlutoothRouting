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
    while socketServeur.actif:
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
    #variable interne
    global enCours_rechercheStandard
    enCours_rechercheStandard = True
    majCouleurs()
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
    #réaffiche la liste
    majListe()

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

def afficheReseau():
    pass

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
bt_quitter = None
liste_peripheriques = None

#fonctions de lancement de threads
def startDecouverteReseau():
    """
        démarre un thread de découverte du réseau
    """
    if interfaceInitialise:
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
    if interfaceInitialise:
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
    if interfaceInitialise:
        global enCours_rechercheReseau
        if not enCours_rechercheReseau:
            enCours_rechercheReseau = True
            t = threading.Thread( target = rechercheReseau )
            t.daemon = True
            t.start()
        majCouleurs()

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
            liste_peripheriques.insert('',"end",values=(k,item["nom"],type ) )

#crée la fenètre
def menu(fenetre):
    #variables
    global bt_decouverte
    global bt_rechercheStd
    global bt_rechercheAv
    global bt_affichage
    global bt_quitter
    global liste_peripheriques
    #création des boutons
    bt_decouverte = Button(fenetre, text = "Découverte", command = startDecouverteReseau)
    bt_rechercheStd = Button(fenetre, text = "Recherche standard", command = startRechercheStandard)
    bt_rechercheAv = Button(fenetre, text = "Recherche avancée", command = startRechercheReseau())
    bt_affichage = Button(fenetre, text = "Mappage reseau", command = lambda: afficheReseau())
    bt_quitter = Button(fenetre, text = "Quitter", command = fenetre.quit)
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
    bt_quitter.grid(row=4,sticky=W+E)
    liste_peripheriques.grid(column=1,row=0,rowspan=5)
    
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

#creation de la fenetre
fenetre = Tk()

menu(fenetre)

#ferme le serveur
socketServeur.close()

    




