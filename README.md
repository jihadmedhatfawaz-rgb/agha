# Restaurant sur WhatsApp : bot + menu en photos

Le client écrit au numéro WhatsApp du restaurant :

1. Il reçoit un message de bienvenue avec deux boutons : **🛒 Commander** et **💬 Un responsable**.
2. **Commander** lui envoie un bouton « Ouvrir le menu » (lien personnel, valable 12 h).
3. Dans le menu, il voit la vraie photo de chaque plat avec sa composition écrite, retire les ingrédients qu'il n'aime pas, ajoute des suppléments, choisit livraison ou à emporter, puis valide.
4. La commande arrive sur WhatsApp : récapitulatif pour le client, et fiche complète pour le(s) responsable(s).
5. **Un responsable** : le bot se met en pause pour ce client et transmet ses messages aux responsables.

## Fichiers

- `menu/index.html` : le menu (photos, compositions, panier).
- `menu/menu.json` : la carte Agha (catégories, plats, tailles et prix, ingrédients retirables, suppléments). **C'est le seul fichier à modifier pour changer la carte.** Il est généré par `tools/build_menu.py` à partir de la transcription `menu/carte-agha-source.md` (carte Agha CI, mai 2024).
- `menu/img/` : les vraies photos des plats, découpées dans la carte.
- `server/server.js` : le bot WhatsApp + le serveur du menu. Node 18 ou plus, aucune dépendance.
- `server/.env.example` : les réglages à remplir.

## Commandes des responsables (à écrire au numéro du restaurant)

| Commande | Effet |
|---|---|
| `/r 2250700000000 Bonjour !` | répondre à un client |
| `/fin 2250700000000` | rendre la main au bot |
| `/ok A123` · `/pret A123` · `/route A123` · `/livre A123` · `/annule A123` | prévenir le client de l'avancement |
| envoyer une **image** avec la légende `/pub` | remplacer la bannière publicitaire en haut du menu |
| `/pub off` | retirer la bannière envoyée (le menu reprend la bannière par défaut de `menu.json`) |

La bannière peut aussi se changer depuis la page **`/admin`** du serveur (mot de passe `ADMIN_KEY` dans `.env`) : choisir une image, « Mettre en ligne ».

## Lancer en local (mode simulation)

```
cd server && node server.js
```

Ouvrir http://localhost:3000/menu. Sans `WA_TOKEN`, rien n'est envoyé : les messages WhatsApp s'affichent dans la console.

## Mettre en ligne

1. **Compte Meta Business** + une app sur developers.facebook.com avec le produit WhatsApp.
2. **Un numéro** dédié ajouté dans WhatsApp Manager : noter le *Phone number ID*.
3. **Jeton permanent** : créer un utilisateur système dans les paramètres Business, lui donner l'app, générer un jeton avec `whatsapp_business_messaging` et `whatsapp_business_management`.
4. **Héberger** `server/` (avec le dossier `menu/` à côté) sur une adresse HTTPS : Render, Railway, un VPS… Mettre l'adresse dans `PUBLIC_URL`.
5. **Webhook** dans l'app Meta : URL `https://votre-domaine/webhook`, jeton de vérification = `WA_VERIFY_TOKEN`, abonnement au champ `messages`. Mettre le secret de l'app dans `WA_APP_SECRET`.
6. Remplir `MANAGER_NUMBERS` avec les numéros des responsables (format international sans +).

À savoir : WhatsApp n'autorise les messages libres que dans les 24 h qui suivent le dernier message reçu. Chaque responsable doit donc écrire au numéro du restaurant une fois par jour, ou il faut faire approuver un modèle de message pour les notifications de commande. Les commandes sont gardées dans `server/data/orders.jsonl`.

## Photos et composition des plats

Chaque carte du catalogue montre la vraie photo du plat, son prix et sa composition écrite. Le client touche un ingrédient pour le retirer : la fiche du plat s'ouvre avec cet ingrédient barré, et il peut y choisir la taille, ajouter des suppléments et une précision pour la cuisine. Les ingrédients marqués d'un point sont la base du plat et ne se retirent pas.

Chaque plat a aussi une vraie photo (`pic` dans `menu.json`, fichiers dans `menu/img/web/`) : photos sous licence libre trouvées sur Openverse (Flickr, Wikimedia Commons), crédit et licence affichés sous la photo, plus les photos envoyées par le restaurant (`agha-*.jpg`). La liste plat → photo est dans `menu/photos.json`, fusionnée par `tools/build_menu.py`. Sur la fiche d'un plat, deux vues pour les 15 plats qui ont aussi une photo dans la carte Agha : « Photo » et « Carte Agha ». Pour changer la photo d'un plat, remplacer le fichier dans `img/web/` ou modifier `photos.json` puis relancer `tools/build_menu.py`.

Les tailles ont chacune leur prix (`sizes`), et un supplément peut coûter un prix différent selon la taille (`price: { "p": 1000, "m": 1500, "g": 2000 }`). Le serveur recalcule toujours le prix lui-même.

Les compositions des burgers, salades et grillades ne sont pas détaillées sur la carte Agha : elles sont déduites du nom du plat (`inferred: true` affiche « Composition indicative »). À faire valider par le restaurant.

## Mise en ligne (Railway)

1. Sur https://railway.com : **New Project → Deploy from GitHub repo →** choisir ce dépôt. Railway lance `npm start` tout seul.
2. Onglet **Settings → Networking → Generate Domain** : c'est l'adresse publique (ex. `https://agha.up.railway.app`).
3. Clic droit sur le service → **Attach volume**, point de montage `/data` (garde les commandes et la bannière).
4. Onglet **Variables** : `PUBLIC_URL` (l'adresse ci-dessus), `DATA_DIR=/data`, `ADMIN_KEY`, `MANAGER_NUMBERS`, puis les réglages WhatsApp (`WA_TOKEN`, `WA_PHONE_NUMBER_ID`, `WA_VERIFY_TOKEN`, `WA_APP_SECRET`).
5. Menu : `PUBLIC_URL/menu` · bannière : `PUBLIC_URL/admin` · webhook Meta : `PUBLIC_URL/webhook`.

Les mots de passe et jetons se mettent **uniquement** dans les variables de l'hébergeur, jamais dans ce dépôt.
