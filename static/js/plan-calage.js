/* Dudu — éditeur de calage des plans importés (M6), « maison »
 * (spec technique, ~150 lignes) : l'image se dépose sur l'orthophoto
 * comme une source MapLibre de type image posée sur ses 4 coins.
 * Trente mètres du quotidien : déplacer l'image d'un glisser, tirer
 * les poignées de coin, régler l'échelle et l'opacité, enregistrer.
 */
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  var conteneur = document.getElementById("carte");
  var donnees = JSON.parse(
    document.getElementById("donnees-calage").textContent
  );
  var champCoins = document.getElementById("id_coins");
  var champOpacite = document.getElementById("id_opacite");
  var reglette = document.getElementById("reglette-opacite");

  if (conteneur === null || typeof maplibregl === "undefined" || !donnees.url) {
    return;
  }

  /* coins : 4 couples [lng, lat] (haut-gauche, haut-droite,
   * bas-droite, bas-gauche) — l'ordre attendu par MapLibre. */
  var coins = donnees.coins.map(function (coin) {
    return [coin[0], coin[1]];
  });

  var carte = new maplibregl.Map({
    container: conteneur,
    style: window.DUDU_STYLE_CARTE,
    center: [donnees.lng, donnees.lat],
    zoom: donnees.zoom,
  });
  carte.addControl(new maplibregl.NavigationControl({ showCompass: false }));
  window.DUDU_DEBLOQUE_GLISSE_FIREFOX(carte);

  function centre() {
    var c = [0, 0];
    coins.forEach(function (coin) {
      c[0] += coin[0];
      c[1] += coin[1];
    });
    return [c[0] / 4, c[1] / 4];
  }

  function serialiser() {
    champCoins.value = JSON.stringify(coins);
  }

  /* Poignées de coin : un marqueur circulaire par coin, draggable. */
  var poignees = [];
  function poserPoignees() {
    poignees.forEach(function (poignee) {
      poignee.remove();
    });
    poignees = coins.map(function (coin, i) {
      var element = document.createElement("div");
      element.className = "poignee";
      element.title = "Poignée de coin " + (i + 1);
      var marqueur = new maplibregl.Marker({ element: element, draggable: true })
        .setLngLat(coin)
        .addTo(carte);
      marqueur.on("drag", function () {
        var position = marqueur.getLngLat();
        coins[i] = [position.lng, position.lat];
        carte.getSource("plan").setCoordinates(coins);
      });
      marqueur.on("dragend", serialiser);
      return marqueur;
    });
  }

  function majPoignees() {
    poignees.forEach(function (poignee, i) {
      poignee.setLngLat(coins[i]);
    });
  }

  var opacite = donnees.opacite;

  carte.on("load", function () {
    carte.addSource("plan", {
      type: "image",
      url: donnees.url,
      coordinates: coins,
    });
    carte.addLayer({
      id: "plan-image",
      type: "raster",
      source: "plan",
      paint: { "raster-opacity": opacite, "raster-fade-duration": 0 },
    });
    poserPoignees();
    serialiser();

    /* Déplacer l'image entière : glisser la couche image (hors
     * poignées) translate les 4 coins ensemble. */
    carte.on("mousedown", "plan-image", function (e) {
      e.preventDefault();
      carte.dragPan.disable();
      var depart = { x: e.point.x, y: e.point.y, coins: coins.map(function (c) { return [c[0], c[1]]; }) };

      function bouger(ev) {
        var dx = ev.point.x - depart.x;
        var dy = ev.point.y - depart.y;
        if (dx === 0 && dy === 0) return;
        /* Chaque coin part de sa position au début du glisser,
         * projetée à l'écran, translatée du déplacement de la
         * souris, puis ramenée en terrain. Simple et robuste. */
        depart.coins.forEach(function (coin, i) {
          var point = carte.project(coin);
          var cible = carte.unproject([point.x + dx, point.y + dy]);
          coins[i] = [cible.lng, cible.lat];
        });
        carte.getSource("plan").setCoordinates(coins);
        majPoignees();
      }

      function relacher() {
        carte.dragPan.enable();
        carte.off("mousemove", bouger);
        document.removeEventListener("mouseup", relacher);
        serialiser();
      }

      carte.on("mousemove", bouger);
      document.addEventListener("mouseup", relacher);
    });
  });

  /* Échelle : agrandir/réduire autour du centre, à facteur fixe. */
  function echelle(facteur) {
    var c = centre();
    coins = coins.map(function (coin) {
      return [c[0] + (coin[0] - c[0]) * facteur, c[1] + (coin[1] - c[1]) * facteur];
    });
    carte.getSource("plan").setCoordinates(coins);
    majPoignees();
    serialiser();
  }
  document.getElementById("agrandir").addEventListener("click", function () {
    echelle(1.25);
  });
  document.getElementById("reduire").addEventListener("click", function () {
    echelle(0.8);
  });

  /* Opacité : à la volée, enregistrée avec le calage. */
  reglette.addEventListener("input", function () {
    opacite = parseFloat(reglette.value);
    carte.setPaintProperty("plan-image", "raster-opacity", opacite);
    champOpacite.value = opacite;
  });
});
