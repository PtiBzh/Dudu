/* Dudu — éditeur de dessin des plans de bâtiments (M6, Terra Draw).
 *
 * Trace le polygone d'un plan sur l'orthophoto : « Tracer » arme le
 * mode polygone, chaque clic pose un sommet, revisiter le premier
 * point ferme la forme. La forme déjà enregistrée s'affiche en
 * relecture (calque pâle) ; le tracé final alimente le champ caché
 * « forme » à l'événement « finish ». L'ordre des <script> compte :
 * maplibre-gl.js, puis terra-draw.umd.js (global terraDraw), puis
 * terra-draw-maplibre-gl-adapter.umd.js (global
 * terraDrawMaplibreGlAdapter).
 */
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  var conteneur = document.getElementById("carte");
  var donnees = JSON.parse(
    document.getElementById("donnees-dessin").textContent
  );
  var champForme = document.getElementById("id_forme");

  if (
    conteneur === null ||
    typeof maplibregl === "undefined" ||
    typeof terraDraw === "undefined" ||
    typeof terraDrawMaplibreGlAdapter === "undefined"
  ) {
    return;
  }

  var carte = new maplibregl.Map({
    container: conteneur,
    style: window.DUDU_STYLE_CARTE,
    center: [donnees.lng, donnees.lat],
    zoom: donnees.zoom,
  });
  carte.addControl(new maplibregl.NavigationControl({ showCompass: false }));
  window.DUDU_DEBLOQUE_GLISSE_FIREFOX(carte);

  var terra = new terraDraw.TerraDraw({
    adapter: new terraDrawMaplibreGlAdapter.TerraDrawMapLibreGLAdapter({
      map: carte,
    }),
    modes: [new terraDraw.TerraDrawPolygonMode()],
  });

  carte.on("load", function () {
    /* Bâtiments déjà tracés ou calés : repères discrets sous le
     * nouveau tracé — on ne dessine pas dans le vide. Pas de popup :
     * pendant le tracé, le clic pose un sommet, on ne lui vole pas. */
    var noeudPlans = document.getElementById("donnees-plans");
    if (noeudPlans !== null && typeof window.DUDU_AJOUTER_PLANS === "function") {
      window.DUDU_AJOUTER_PLANS(
        carte,
        JSON.parse(noeudPlans.textContent),
        { popup: false }
      );
    }

    /* Relecture : la forme enregistrée sert de repère pendant le
     * nouveau tracé. */
    if (donnees.forme) {
      carte.addSource("forme-precedente", {
        type: "geojson",
        data: { type: "Feature", geometry: donnees.forme, properties: {} },
      });
      carte.addLayer({
        id: "forme-precedente",
        type: "fill",
        source: "forme-precedente",
        paint: {
          "fill-color": donnees.couleur,
          "fill-opacity": 0.2,
        },
      });
      carte.addLayer({
        id: "forme-precedente-contour",
        type: "line",
        source: "forme-precedente",
        paint: {
          "line-color": donnees.couleur,
          "line-width": 2,
          "line-dasharray": [3, 2],
        },
      });
    }
    terra.start();
  });

  terra.on("finish", function (id) {
    var feature = terra.getSnapshotFeature(id);
    if (feature && feature.geometry) {
      champForme.value = JSON.stringify(feature.geometry);
    }
  });

  document.getElementById("tracer").addEventListener("click", function () {
    terra.clear();
    champForme.value = "";
    terra.setMode("polygon");
  });

  document.getElementById("effacer").addEventListener("click", function () {
    terra.clear();
    champForme.value = "";
  });
});
