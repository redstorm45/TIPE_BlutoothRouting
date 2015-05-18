# -*- coding: utf-8 -*-

"""

    Ce projet est un essai de routage similaire à celui du web,
    mais appliqué au bluetooth.

    Le routeur est un programme hôte des périphériques,
    permettant un mappage réseau (découverte réseau),
    et du transfert de donnée d'un réseau à un autre.

    Tous les périphériques possèdent un port utilisé par le serveur,
    et un autre pour le client. Ainsi, il se connecte à tous les périphériques
    qu'il trouve à proximité avec ce protocole

    Ce programme utilise la bibliothèque pybluez

    versions:
        python 3.3.5
        pybluez 0.20 for python 3.3

"""

import bluetooth


##  paramètres du programme

UUID_Serveur = "67b7a1d0-fd7b-11e4-b939-0800200c9a66"
UUID_Client  = "67b7a1d1-fd7b-11e4-b939-0800200c9a66"

## fonctions

def initialisation():
    """
        Active la découverte Bluetooth du périphérique,
        et démarre les service appropriés sur les ports.
    
    """

def decouverteReseau(periph):
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
        :return: None
    """

def listeComplet():
    """
        Donne une liste complète du réseau
        
        :return: liste des éléments par leur adresses
            
        
    """
    
def mappageComplet():
    """
        Donne une carte complète du réseau,
        sous forme de dictionnaires imbriqués
        
        :return: liste des éléments par leur adresses
            
        
    """






