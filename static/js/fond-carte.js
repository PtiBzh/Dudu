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
