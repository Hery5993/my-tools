# README - Crypto App

## Description

Crypto App est une application desktop permettant de chiffrer et déchiffrer des fichiers à l’aide d’un mot de passe utilisateur.  
L’application utilise un chiffrement moderne basé sur AES-GCM avec dérivation de clé via Scrypt.

Elle fournit une interface graphique avec deux fonctionnalités principales :
- Chiffrement de fichiers
- Déchiffrement de fichiers

---

## Fonctionnalités

- Chiffrement de fichiers avec mot de passe
- Déchiffrement sécurisé
- Dérivation de clé avec Scrypt
- Chiffrement AES-GCM authentifié
- Interface graphique avec Tkinter et CustomTkinter
- Sélection de fichiers via explorateur système
- Affichage / masquage du mot de passe

---

## Technologies utilisées

- Python 3.10+ (recommandé 3.11)
- Tkinter / CustomTkinter
- cryptography (AES-GCM, Scrypt)

---

## Installation sous Linux

### 1. Installer Python et dépendances système

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk python3-venv