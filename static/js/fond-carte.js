/* Dudu — socle commun des cartes (M3).
 *
 * Style MapLibre minimal : fond raster orthophoto IGN servi par la
 * géoplateforme (tuiles WMTS Web Mercator « PM »). Chargé avant
 * carte.js et choix-position.js ; expose window.DUDU_STYLE_CARTE.
 */
"use strict";

var DUDU_ORTHO_IGN =
  "https://data.geopf.fr/wmts" +
  "?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile" +
  "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS" +
  "&TILEMATRIXSET=PM&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}" +
  "&STYLE=normal&FORMAT=image/jpeg";

var DUDU_STYLE_CARTE = {
  version: 8,
  sources: {
    ortho: {
      type: "raster",
      tiles: [DUDU_ORTHO_IGN],
      tileSize: 256,
      maxzoom: 19,
      attribution: "Orthophoto : IGN — Géoplateforme",
    },
  },
  layers: [{ id: "fond-ortho", type: "raster", source: "ortho" }],
};

window.DUDU_STYLE_CARTE = DUDU_STYLE_CARTE;

/* Firefox : une sélection de texte qui traverse le canvas (glisser démarré
 * dans un texte de la page, ou dans une popup) survit au relâchement.
 * Chaque mousedown suivant tombe alors « dans » cette sélection : Firefox
 * déclenche un glisser natif — un fantôme de la carte suit le curseur et
 * disparaît au relâchement — au lieu de laisser MapLibre paner.
 * user-select:none n'y change rien ; le seul correctif connu est d'effacer
 * la sélection au mousedown (phase de capture, avant MapLibre). Le texte
 * des popups reste sélectionnable : elles vivent hors du canvas.
 * (Mécanisme confirmé : paulwaite87/atmos-gl PR #419, oct. 2026.) */
window.DUDU_DEBLOQUE_GLISSE_FIREFOX = function (carte) {
  "use strict";
  var canvas = carte.getCanvasContainer();
  canvas.addEventListener("mousedown", function () {
    var selection = window.getSelection();
    if (selection !== null && !selection.isCollapsed) {
      selection.removeAllRanges();
    }
  }, true);
};

/* Popup partagé des cartes : le HTML vient du DOM côté appelant
 * (textContent), jamais d'une chaîne concaténée avec des saisies. */
window.DUDU_POPUP_SUR = function (carte, lng, lat, html) {
  new maplibregl.Popup({ closeButton: false, offset: 12 })
    .setLngLat([lng, lat])
    .setHTML(html)
    .addTo(carte);
};

/* Centre d'un polygone de coins WGS84 (plans de bâtiments). */
function duduCentreDe(points) {
  var c = [0, 0];
  points.forEach(function (p) {
    c[0] += p[0];
    c[1] += p[1];
  });
  return [c[0] / points.length, c[1] / points.length];
}

/* Plans de bâtiments (M6) en couches, sous tout ce qui est déjà
 * affiché : triés par ordre puis ajoutés — le dernier ajout recouvre.
 * Partagé par la grande carte (M3) et les mini-cartes de saisie.
 *
 * options.couchesPrioritaires : couches (marqueurs, pastilles) qui
 *   gardent la main au clic. Un plan sous un marqueur ne « prend »
 *   jamais son clic — un poste superposé à un bâtiment reste
 *   cliquable (bug remonté en exploitation).
 * options.popup : titre du plan au clic (défaut : oui). La mini-carte
 *   de saisie le coupe : là, le clic place le marqueur.
 * options.etiquettes : nom du bâtiment affiché en permanence sur la
 *   carte (défaut : oui). */
/* Étiquette de plan clouée à sa position : un marqueur DOM, pas une
 * couche symbole — le style n'embarque pas de serveur de glyphes
 * (text-field exigerait style.glyphs). Un <div> en pointer-events:none
 * laisse passer les clics : le poste posé sur le bâtiment garde la
 * main. Le texte passe par textContent : jamais de HTML injecté. */
var duduEtiquetteSur = function (carte, lng, lat, texte) {
  var element = document.createElement("div");
  element.className = "etiquette-plan";
  element.textContent = texte;
  new maplibregl.Marker({ element: element })
    .setLngLat([lng, lat])
    .addTo(carte);
};

window.DUDU_AJOUTER_PLANS = function (carte, plans, options) {
  "use strict";
  var options = options || {};
  var couches = options.couchesPrioritaires || [];

  function clicLibre(e) {
    var presentes = couches.filter(function (id) {
      return carte.getLayer(id) !== undefined;
    });
    if (presentes.length === 0) return true;
    return (
      carte.queryRenderedFeatures(e.point, { layers: presentes })
        .length === 0
    );
  }

  function titreDe(plan) {
    var boite = document.createElement("div");
    var fort = document.createElement("strong");
    fort.textContent =
      plan.nom + (plan.etiquette ? " — " + plan.etiquette : "");
    boite.appendChild(fort);
    return boite.innerHTML;
  }

  plans
    .slice()
    .sort(function (a, b) {
      return (a.ordre || 0) - (b.ordre || 0);
    })
    .forEach(function (plan) {
      if (plan.nature === "forme" && plan.forme) {
        var id = "plan-forme-" + plan.id;
        carte.addSource(id, {
          type: "geojson",
          data: { type: "Feature", geometry: plan.forme, properties: {} },
        });
        carte.addLayer({
          id: id,
          type: "fill",
          source: id,
          paint: {
            "fill-color": plan.couleur,
            "fill-opacity": Math.min(0.9, plan.opacite * 0.9),
          },
        });
        carte.addLayer({
          id: id + "-contour",
          type: "line",
          source: id,
          paint: {
            "line-color": plan.couleur,
            "line-width": 2,
            "line-opacity": 0.9,
          },
        });
        carte.on("click", id, function (e) {
          if (options.popup === false || !clicLibre(e)) return;
          var centre = duduCentreDe(plan.forme.coordinates[0]);
          window.DUDU_POPUP_SUR(carte, centre[0], centre[1], titreDe(plan));
        });
      } else if (plan.nature === "image" && plan.url && plan.coins) {
        var idImage = "plan-image-" + plan.id;
        carte.addSource(idImage, {
          type: "image",
          url: plan.url,
          coordinates: plan.coins,
        });
        carte.addLayer({
          id: idImage,
          type: "raster",
          source: idImage,
          paint: {
            "raster-opacity": plan.opacite,
            "raster-fade-duration": 0,
          },
        });
        carte.on("click", idImage, function (e) {
          if (options.popup === false || !clicLibre(e)) return;
          var centre = duduCentreDe(plan.coins);
          window.DUDU_POPUP_SUR(carte, centre[0], centre[1], titreDe(plan));
        });
      }

      /* Nom du bâtiment en permanence, au centre du plan. */
      if (options.etiquettes !== false) {
        var centre =
          plan.nature === "image" && plan.coins
            ? duduCentreDe(plan.coins)
            : duduCentreDe(plan.forme.coordinates[0]);
        duduEtiquetteSur(
          carte,
          centre[0],
          centre[1],
          plan.nom + (plan.etiquette ? " — " + plan.etiquette : "")
        );
      }
    });
};
