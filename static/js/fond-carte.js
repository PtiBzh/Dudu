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
