# -*- coding: utf-8 -*-
"""
@file        hw_mux_adg731.py
@brief       Pilote pour multiplexeur ADG731 via interface SPI.
@details     Ce module fournit un pilote pour contrôler les multiplexeurs
             ADG731 via l'interface SPI0. Supporte jusqu'à 4 cartes avec
             32 canaux chacune. Gère la configuration SPI et l'envoi des
             commandes de contrôle pour la sélection des canaux.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Opérations sur les fichiers et chemins système
import os
# Interface SPI pour Linux
import spidev

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def adg731_ctrl_byte(address, enable=True):
    """
    @brief   Génère le byte de contrôle pour l'ADG731.
    @details Construit l'octet de commande selon le protocole ADG731 avec
             le bit d'activation (EN) en MSB et l'adresse sur 5 bits.
             L'activation se fait avec EN=0 (logique inversée).

    @param   address Adresse du canal (0-31).
    @param   enable  État d'activation du canal (True=activé).

    @return  Octet de contrôle formaté selon le protocole ADG731.

    @exception ValueError Si l'adresse est hors de la plage valide.
    """
    # Vérification de la plage d'adresse valide
    if address < 0 or address > 31:
        # Lever une exception si l'adresse est invalide
        raise ValueError("address out of range (0..31)")
    # Logique inversée pour le bit d'activation
    if enable is True:
        # EN=0 pour activer (logique inversée)
        en = 0
    else:
        # EN=1 pour désactiver
        en = 1
    # Construction de l'octet de contrôle (EN << 7) | (adresse & 0x1F)
    ctrl = (en << 7) | (address & 0x1F)
    return ctrl

# ---------------------------------------------------------------------------
# Classes principales
# ---------------------------------------------------------------------------

class Adg731MuxSpi:
    """
    @brief   Pilote SPI pour multiplexeurs ADG731.
    @details Classe pour contrôler jusqu'à 4 multiplexeurs ADG731 via
             l'interface SPI0. Chaque multiplexeur peut gérer 32 canaux.
             Configure automatiquement les paramètres SPI optimaux et
             gère la communication avec les circuits.
    """
    
    # Chemins des périphériques SPI disponibles
    DEV = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev0.2", "/dev/spidev0.3"]

    def __init__(self, speed_hz=100000):
        """
        @brief   Initialise le pilote pour les multiplexeurs ADG731.
        @details Configure l'interface SPI pour chaque canal disponible,
                 définit les paramètres de communication et initialise
                 les handles pour jusqu'à 4 cartes multiplexeurs.

        @param   speed_hz Vitesse SPI en Hz (par défaut 100kHz).
        """
        # Stockage de la vitesse SPI configurée
        self.speed = speed_hz
        # Liste des handles SPI pour chaque carte
        self.handles = []
        # Index de boucle pour initialisation des cartes
        index = 0
        # Boucle d'initialisation pour les 4 cartes possibles
        while index < 4:
            # Récupération du chemin du périphérique SPI
            path = self.DEV[index]
            # Vérification de l'existence du périphérique
            if os.path.exists(path) is True:
                # Création d'une instance SpiDev
                s = spidev.SpiDev()
                # Ouverture du bus SPI (bus 0, device index)
                s.open(0, index)
                # Configuration du mode SPI (mode 1: CPOL=0, CPHA=1)
                s.mode = 1
                # Configuration de la vitesse maximale
                s.max_speed_hz = self.speed
                # Configuration du nombre de bits par mot
                s.bits_per_word = 8
                try:
                    # Configuration LSB first (False = MSB first)
                    s.lsbfirst = False
                except Exception:
                    # Ignorer si non supporté par la plateforme
                    pass
                try:
                    # Configuration CS high (False = CS actif bas)
                    s.cshigh = False
                except Exception:
                    # Ignorer si non supporté par la plateforme
                    pass
                try:
                    # Configuration no CS (False = utiliser CS)
                    s.no_cs = False
                except Exception:
                    # Ignorer si non supporté par la plateforme
                    pass
                try:
                    # Configuration three wire (False = mode 4 fils)
                    s.threewire = False
                except Exception:
                    # Ignorer si non supporté par la plateforme
                    pass
                # Ajout du handle configuré à la liste
                self.handles.append(s)
            else:
                # Ajout d'un handle None si le périphérique n'existe pas
                self.handles.append(None)
            # Passage à l'index suivant
            index = index + 1

    def close(self):
        """
        @brief   Ferme toutes les interfaces SPI.
        @details Parcourt tous les handles SPI ouverts et les ferme
                 proprement. Gère les erreurs de fermeture pour éviter
                 les exceptions lors du nettoyage.
        """
        # Parcours de tous les handles SPI
        for h in self.handles:
            # Vérification que le handle existe
            if h is not None:
                try:
                    # Fermeture du handle SPI
                    h.close()
                except Exception:
                    # Ignorer les erreurs de fermeture
                    pass

    def set_channel(self, board_index, address):
        """
        @brief   Active un canal spécifique sur une carte donnée.
        @details Envoie la commande de sélection de canal vers la carte
                 multiplexeur spécifiée. Génère l'octet de contrôle et
                 l'envoie via SPI.

        @param   board_index Index de la carte (0-3).
        @param   address     Adresse du canal à activer (0-31).

        @return  Octet de contrôle envoyé, ou None si erreur.

        @exception ValueError Si l'index de carte est hors plage.
        """
        # Vérification de la plage d'index de carte
        if board_index < 0 or board_index > 3:
            # Lever une exception si l'index est invalide
            raise ValueError("board_index out of range (0..3)")
        # Récupération du handle SPI pour la carte
        h = self.handles[board_index]
        # Vérification de l'existence du handle
        if h is None:
            print("ADG731: board", board_index, "non présent, ignoré")
            return None
        # Génération de l'octet de contrôle pour activer le canal
        ctrl = adg731_ctrl_byte(address, True)
        # Envoi de la commande via SPI
        h.xfer2([ctrl])
        return ctrl

    def set_output_channel(self, channel_index):
        """
        @brief   Utilitaire simple pour sélectionner un canal de sortie.
        @details Fonction de commodité qui utilise automatiquement la
                 carte 0 et mappe directement l'index de canal sur
                 l'adresse du multiplexeur.

        @param   channel_index Index du canal de sortie (0-31).

        @return  Octet de contrôle envoyé, ou None si erreur.

        @exception ValueError Si l'index de canal est hors plage.
        """
        # Utilitaire simple si tu veux piloter par numéro de voie unique
        # ici: board 0, address = channel_index
        # Vérification de la plage d'index de canal
        if channel_index < 0 or channel_index > 31:
            # Lever une exception si l'index est invalide
            raise ValueError("channel_index out of range (0..31)")
        # Appel de la méthode générique avec la carte 0
        return self.set_channel(0, channel_index)
