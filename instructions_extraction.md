J'ai des PDF de catalogues promotionnels de supermarchés suisses dans le
dossier ./catalogues/. Je veux que tu fasses ce qui suit, étape par étape :

ÉTAPE 1 — Conversion
Pour chaque PDF du dossier, convertis chaque page en image PNG (200 dpi)
dans un sous-dossier ./images/[nom_du_pdf]/page_001.png, page_002.png, etc.
Utilise PyMuPDF (fitz) en Python, installe-le si nécessaire.

ÉTAPE 2 — Extraction des données
Pour chaque image PNG générée, regarde-la toi-même (utilise ton propre
outil de lecture d'image, ne passe pas par l'API Anthropic) et repère
TOUS les produits alimentaires présentés avec un prix sur la page, qu'ils
soient en promotion ou non.

SI un produit n'est PAS un produit alimentaire (ex : produits
d'entretien, cosmétiques, vaisselle, décoration, hygiène, textile,
électroménager, articles pour animaux, fleurs et plantes, etc.),
IGNORE-LE COMPLÈTEMENT : ne crée aucune ligne, aucune entrée, même
temporaire, pour ce produit. Il ne doit jamais apparaître dans aucun
fichier intermédiaire ni dans le résultat final.

Pour chaque produit ALIMENTAIRE, extrais les champs suivants :

- produit : nom du produit tel qu'affiché
- souscategorie_pyramide : identifie le code de la sous-catégorie qui
  correspond le mieux au produit (ex : "1.1", "5.5"), en te basant sur
  cette liste fermée :
     1.1 Eau nature (plate ou gazeuse)
     1.2 Eau aromatisée (sans sucres ajoutés)
     1.3 Jus de fruits 100% fruits
     1.4 Autres (ex. café en poudre, café instantané, capsules de café, thé)
     2.1 Fruits
     2.2 Légumes (y compris tomates en conserve et sauces 100% tomate)
     3.1 Pains
     3.2 Riz
     3.3 Pâtes (nature)
     3.4 Pommes de terre
     3.5 Autres (les pâtes farcies vont en 7.5, les farines en 10.2)
     (ATTENTION : les légumineuses ne vont PAS en catégorie 3, voir 5.5)
     4.1 Fromage
     4.2 Yogourts aromatisés, séré aromatisé
     4.3 Yogourts nature, fromage blanc, séré nature
     4.4 Boissons lactées sans sucre ajoutés
     4.5 Autres
     5.1 Viande hors charcuterie
     5.2 Charcuterie
     5.3 Poisson (y compris conserves de poisson simples : thon, sardines,
         hareng ; les pâtés et pâtes à tartiner de poisson vont en 7.2)
     5.4 Œufs
     5.5 Légumineuses (hors houmous, voir 7.2)
     5.6 Autres (ex. tofu et alternatives végétales riches en protéines ;
         c'est la teneur en protéines qui est déterminante)
     6.1 Beurre
     6.2 Huile (y compris huile d'olive)
     6.3 Crème
     6.4 Noix et graines (uniquement si non salées)
     6.5 Autres (ex. lait de coco, margarine, mayonnaise)
     7.1 Sucreries (y compris müesli, birchermüesli et granola)
     7.2 Snacks salés (y compris olives en sachet ou en conserve, houmous,
         garnitures pour bruschetta, snacks feuilletés, pâtés et pâtes à
         tartiner salées de poisson, de viande ou de légumes, p. ex. pâté
         de saumon, tartinable à la tomate)
     7.3 Boissons sucrées (y compris boissons sucrées sans alcool,
         boissons protéinées et boissons lactées avec sucres ajoutés)
     7.4 Boissons alcoolisées (ATTENTION : Migros ne vend pas d'alcool ;
         tout produit Migros qui ressemble à une boisson alcoolisée est
         sans alcool et va en 7.3)
     7.5 Plats préparés, pizzas, pâtes farcies, pâtes à tarte toutes
         prêtes, préparations panées à base de viande ou de poisson (ex.
         nuggets, escalopes panées, bâtonnets de poisson)
     8.1 Produits pour bébé (ex. bouillies pour bébé, desserts pour bébé,
         lait en poudre pour bébé)
     9.1 Compléments alimentaires (ex. whey protéinée en poudre)
     10.1 Sauces et condiments (ex. sauces à salade, sauces pour pâtes qui
          ne sont pas 100% tomate, arôme Maggi, sel, épices, vinaigre,
          ajvar)
     10.2 Ingrédients bruts (ex. levure, poudre à lever, bicarbonate,
          farine fleur, farine pour tresse, farine à pizza)
  NE DÉTERMINE PAS de catégorie principale séparément : elle sera
  calculée automatiquement à partir de ce code (voir ÉTAPE 3).
  Concentre-toi uniquement sur le choix de la sous-catégorie la plus
  précise.

- type_poisson : UNIQUEMENT si souscategorie_pyramide = "5.3" ET que
  la mention "élevage" ou "sauvage" est visible sur l'image. Sinon null.
- provenance : pays d'origine si indiqué, sinon null
- label_1, label_2, label_3 : si un produit a plusieurs labels visibles
  (Bio, IP-Suisse, Demeter, Fairtrade, MSC, etc.), reporte-les dans des
  colonnes séparées label_1, label_2, label_3 (dans l'ordre où ils
  apparaissent). Laisse à null les colonnes non utilisées. Si aucun
  label, tout à null.
- type_offre_1, type_offre_2, type_offre_3 : si un produit a plusieurs
  types d'offre visibles (ex : "2 pour 1" ET "carte de fidélité"),
  reporte-les dans des colonnes séparées type_offre_1, type_offre_2,
  type_offre_3. Laisse à null les colonnes non utilisées.
- prix_initial : prix barré/initial si affiché (nombre, en CHF, sans
  symbole). Pour un produit sans promotion, c'est le prix affiché.
  Sinon null.
- prix_final : prix promotionnel affiché (nombre), sinon null
- page : numéro de page
- fichier_source : nom du PDF d'origine

PRODUITS ALIMENTAIRES SANS PROMOTION : un produit alimentaire affiché
avec un prix mais sans aucun rabais ni offre propre à ce produit (pas
de pourcentage, de prix barré, de mention "Action", "Hit", "2+1", etc.)
doit AUSSI figurer dans la liste. Dans ce cas, laisse vides
type_offre_1/2/3, prix_final, rabais_montant et rabais_pourcentage, et
mets le prix affiché dans prix_initial. Un simple bandeau de page (ex :
"Jusqu'à 33% d'économies", "Prix mini") ou une mention "Nouveauté"
ne compte pas comme une offre propre au produit.

RÈGLES IMPORTANTES :
- N'invente RIEN. Si une info n'est pas visible ou lisible, mets null.
- Ne déduis pas la provenance, les labels ou le type de poisson s'ils
  ne sont pas écrits explicitement sur l'image.
- Un même produit qui apparaît sur plusieurs pages = plusieurs lignes
  distinctes (ne pas dédupliquer).
- Traite les images une par une ou par petits lots, pas toutes en même
  temps.

ÉTAPE 3 — Dérivation de la catégorie principale
Pour chaque ligne extraite, calcule categorie_pyramide en extrayant
automatiquement le chiffre avant le point de souscategorie_pyramide
(ex : "5.5" → 5, "1.2" → 1, "10.2" → 10). Ne redemande jamais ce choix au
modèle : c'est un calcul, pas une nouvelle classification.

Dans l'Excel, affiche la catégorie et la sous-catégorie avec les
libellés suivants (déterminés uniquement à partir du code choisi) :

Catégorie :
  1. Boissons
  2. Fruits et légumes
  3. Produits céréaliers et pommes de terre
  4. Produits laitiers
  5. Légumineuses, œufs, viande et autres
  6. Huiles, matière grasse, graines et oléagineux
  7. Boissons sucrées, sucreries, snacks salés, plats préparés et condiments
  8. Produits pour bébé
  9. Compléments alimentaires
  10. Condiments et ingrédients

Sous-catégorie :
  1.1 Eau nature
  1.2 Eau aromatisée
  1.3 Jus de fruits 100% fruits
  1.4 Autres
  2.1 Fruits
  2.2 Légumes
  3.1 Pains
  3.2 Riz
  3.3 Pâtes
  3.4 Pommes de terre
  3.5 Autres
  4.1 Fromage
  4.2 Yogourts et séré aromatisés
  4.3 Yogourts et séré nature
  4.4 Boissons lactées sans sucre ajoutés
  4.5 Autres
  5.1 Viande hors charcuterie
  5.2 Charcuterie
  5.3 Poisson
  5.4 Œufs
  5.5 Légumineuses
  5.6 Autres
  6.1 Beurre
  6.2 Huile
  6.3 Crème
  6.4 Noix et graines
  6.5 Autres
  7.1 Sucreries
  7.2 Snacks salés
  7.3 Boissons sucrées
  7.4 Boissons alcoolisées
  7.5 Plats préparés, pizzas, pâtes farcies, préparations panées
  8.1 Produits pour bébé
  9.1 Compléments alimentaires
  10.1 Sauces et condiments
  10.2 Ingrédients bruts

ÉTAPE 4 — Calcul du rabais
Pour chaque ligne où prix_initial ET prix_final sont connus, calcule :
- rabais_montant = prix_initial - prix_final
- rabais_pourcentage = (prix_initial - prix_final) / prix_initial * 100
  (arrondi à 1 décimale)
Laisse ces deux champs à null si l'un des deux prix manque.

ÉTAPE 5 — Export
Rassemble toutes les lignes de tous les catalogues dans un seul fichier
Excel (.xlsx) nommé promotions_extraites.xlsx, avec une ligne d'en-tête
claire. Colonnes dans cet ordre : fichier_source, page, produit,
categorie_pyramide, souscategorie_pyramide, provenance, type_poisson,
label_1, label_2, label_3, type_offre_1, type_offre_2, type_offre_3,
prix_initial, prix_final, rabais_montant, rabais_pourcentage. Trie par
fichier_source puis par page.

Avant de commencer, dis-moi combien de PDF et environ combien de pages
au total tu as détectés, pour que je sache à quoi m'attendre en termes
de temps de traitement.
