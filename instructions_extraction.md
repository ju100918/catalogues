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
     2.2 Légumes (y compris tomates en conserve, garnitures de légumes)
     3.1 Pains
     3.2 Riz
     3.3 Pâtes (nature)
     3.4 Pommes de terre
     3.5 Autres (ex. pâtes farcies, plats tout prêts à base de céréales)
     (ATTENTION : les légumineuses ne vont PAS en catégorie 3, voir 5.5)
     4.1 Fromage
     4.2 Yogourts aromatisés, séré aromatisé
     4.3 Yogourts nature, fromage blanc, séré nature
     4.4 Boissons lactées sans sucre ajoutés
     4.5 Autres
     5.1 Viande hors charcuterie
     5.2 Charcuterie
     5.3 Poisson
     5.4 Œufs
     5.5 Légumineuses (hors houmous, voir 7.2)
     5.6 Autres
     6.1 Beurre
     6.2 Huile (y compris huile d'olive)
     6.3 Crème
     6.4 Noix et graines (uniquement si non salées)
     6.5 Autres (ex. lait de coco, margarine, mayonnaise, sauce à salade)
     7.1 Sucreries (y compris müesli, birchermüesli et granola)
     7.2 Snacks salés (y compris olives en sachet ou en conserve, houmous,
         snacks feuilletés)
     7.3 Boissons sucrées (y compris boissons sucrées sans alcool,
         boissons protéinées et boissons lactées avec sucres ajoutés)
     7.4 Boissons alcoolisées
     7.5 Autres (ex. pizzas, sauces et condiments comme l'arôme Maggi)
     8.1 Produits pour bébé (ex. bouillies pour bébé, desserts pour bébé,
         lait en poudre pour bébé)
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
(ex : "5.5" → 5, "1.2" → 1, "8.1" → 8). Ne redemande jamais ce choix au
modèle : c'est un calcul, pas une nouvelle classification.

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
categorie_pyramide, souscategorie_pyramide, type_poisson, provenance,
label_1, label_2, label_3, type_offre_1, type_offre_2, type_offre_3,
prix_initial, prix_final, rabais_montant, rabais_pourcentage. Trie par
fichier_source puis par page.

Avant de commencer, dis-moi combien de PDF et environ combien de pages
au total tu as détectés, pour que je sache à quoi m'attendre en termes
de temps de traitement.
