/* Dudu — carte des postes et actions (M3, MapLibre GL JS).
 *
 * Les données sont sérialisées par Django dans <script
 * id="donnees-carte"> (filtre json_script) : postes positionnés avec
 * couleur (gravité santé/sécurité) et halo (satisfaction), plus
 * actions ouvertes liées à ces postes. Marqueurs rendus en couches
 * « circle » GeoJSON ; clic → popup avec lien vers la fiche.
 * Le paramètre data-poste (?poste=pk) centre la vue sur un poste.
 */
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  var conteneur = document.getElementById("carte");
  if (conteneur === null || typeof maplibregl === "undefined") return;

  var donnees = JSON.parse(
    document.getElementById("donnees-carte").textContent
  );

  var carte = new maplibregl.Map({
    container: conteneur,
    style: window.DUDU_STYLE_CARTE,
    center: [
      parseFloat(conteneur.dataset.lng),
      parseFloat(conteneur.dataset.lat),
    ],
    zoom: parseFloat(conteneur.dataset.zoom),
  });
  carte.addControl(new maplibregl.NavigationControl({ showCompass: false }));

  /* Données vers GeoJSON : MapLibre attend [longitude, latitude]. */
  function enGeojson(elements) {
    return {
      type: "FeatureCollection",
      features: elements.map(function (e) {
        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [e.lng, e.lat],
          },
          properties: e,
        };
      }),
    };
  }

  /* HTML de popup construit par le DOM : textContent échappe les
   * noms saisis par l'équipe, sans bidouille de chaînes. */
  function htmlPopup(p, libelleLien) {
    var boite = document.createElement("div");
    var fort = document.createElement("strong");
    fort.textContent = p.nom || p.intitule;
    boite.append(fort, document.createElement("br"));
    if (p.statut) {
      var statut = document.createElement("span");
      statut.textContent = "Statut : " + p.statut;
      boite.append(statut, document.createElement("br"));
    }
    var lien = document.createElement("a");
    lien.href = p.url;
    lien.textContent = libelleLien;
    boite.append(lien);
    return boite.innerHTML;
  }

  function popupSur(lng, lat, html) {
    new maplibregl.Popup({ closeButton: false, offset: 12 })
      .setLngLat([lng, lat])
      .setHTML(html)
      .addTo(carte);
  }

  carte.on("load", function () {
    carte.addSource("postes", {
      type: "geojson",
      data: enGeojson(donnees.postes),
    });
    carte.addSource("actions", {
      type: "geojson",
      data: enGeojson(donnees.actions),
    });

    /* Halo de satisfaction, dessous (conditions de revue, M4). */
    carte.addLayer({
      id: "postes-halo",
      type: "circle",
      source: "postes",
      filter: ["has", "halo"],
      paint: {
        "circle-color": ["get", "halo"],
        "circle-opacity": 0.45,
        "circle-radius": 14,
      },
    });
    /* Marqueur du poste : remplissage = gravité santé/sécurité. */
    carte.addLayer({
      id: "postes",
      type: "circle",
      source: "postes",
      paint: {
        "circle-color": [
          "case",
          ["has", "couleur"],
          ["get", "couleur"],
          "#6b7684",
        ],
        "circle-opacity": 0.95,
        "circle-radius": 9,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.5,
      },
    });
    /* Actions ouvertes : petites pastilles turquoise. */
    carte.addLayer({
      id: "actions",
      type: "circle",
      source: "actions",
      paint: {
        "circle-color": "#0d6b7c",
        "circle-opacity": 0.9,
        "circle-radius": 5,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1,
      },
    });

    [["postes", "Ouvrir le poste"], ["actions", "Ouvrir l'action"]].forEach(
      function (couche) {
        var idCouche = couche[0];
        var libelle = couche[1];
        carte.on("mouseenter", idCouche, function () {
          carte.getCanvas().style.cursor = "pointer";
        });
        carte.on("mouseleave", idCouche, function () {
          carte.getCanvas().style.cursor = "";
        });
        carte.on("click", idCouche, function (e) {
          var p = e.features[0].properties;
          popupSur(p.lng, p.lat, htmlPopup(p, libelle));
        });
      }
    );

    /* ?poste=pk : centrer et ouvrir la fiche du poste visé. */
    var cible = conteneur.dataset.poste;
    if (cible) {
      var poste = donnees.postes.find(function (p) {
        return String(p.id) === String(cible);
      });
      if (poste) {
        carte.flyTo({ center: [poste.lng, poste.lat], zoom: 17 });
        popupSur(poste.lng, poste.lat, htmlPopup(poste, "Ouvrir le poste"));
      }
    }
  });
});
