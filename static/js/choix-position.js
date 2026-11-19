/* Dudu — choix de position sur mini-carte (M3, MapLibre GL JS).
 *
 * Sert aux formulaires de poste (position obligatoire) et d'action
 * (optionnelle, héritée du poste) : un clic ou un glisser de marqueur
 * alimente les champs cachés .coord-lat / .coord-lng du formulaire.
 */
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  var conteneur = document.getElementById("mini-carte");
  if (conteneur === null || typeof maplibregl === "undefined") return;

  var champLat = document.querySelector(".coord-lat");
  var champLng = document.querySelector(".coord-lng");
  var annonce = document.getElementById("position-choisie");
  if (champLat === null || champLng === null) return;

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
  window.DUDU_DEBLOQUE_GLISSE_FIREFOX(carte);

  /* Plans de bâtiments sous le marqueur : situer un poste sans voir
   * le Hangar, c'est dur. Pas de popup au clic sur un plan : le clic
   * de la mini-carte place le marqueur, on ne le lui vole pas. */
  var noeudPlans = document.getElementById("donnees-plans");
  if (noeudPlans !== null) {
    carte.on("load", function () {
      window.DUDU_AJOUTER_PLANS(
        carte,
        JSON.parse(noeudPlans.textContent),
        { popup: false }
      );
    });
  }

  var marqueur = null;

  function champsAJour() {
    var position = marqueur.getLngLat();
    champLat.value = position.lat;
    champLng.value = position.lng;
    if (annonce !== null) {
      annonce.textContent =
        "Position : " +
        position.lat.toFixed(5) +
        ", " +
        position.lng.toFixed(5);
    }
  }

  function placer(lat, lng) {
    if (marqueur === null) {
      marqueur = new maplibregl.Marker({
        color: "#0d6b7c",
        draggable: true,
      })
        .setLngLat([lng, lat])
        .addTo(carte);
      marqueur.on("dragend", champsAJour);
    } else {
      marqueur.setLngLat([lng, lat]);
    }
    champsAJour();
  }

  carte.on("click", function (e) {
    placer(e.lngLat.lat, e.lngLat.lng);
  });

  /* Position déjà connue (édition, héritage du poste) : l'afficher. */
  var latInitiale = parseFloat(champLat.value);
  var lngInitiale = parseFloat(champLng.value);
  if (!isNaN(latInitiale) && !isNaN(lngInitiale)) {
    placer(latInitiale, lngInitiale);
  }
});
